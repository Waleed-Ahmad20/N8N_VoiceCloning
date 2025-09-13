import os
import torch
import torchaudio
from openvoice import se_extractor
from openvoice.api import ToneColorConverter, BaseSpeakerTTS
import numpy as np
import soundfile as sf

class VoiceProcessor:
    def __init__(self):
        self.device = "cpu"  # CPU only version
        self.ckpt_converter = "checkpoints/converter_v2.pth"
        self.ckpt_base = "checkpoints/base_en_v2.pth"
        self.config_path = "checkpoints/config_en_v2.json"
        self.output_dir = "voices/outputs"
        self.upload_dir = "voices/uploads"
        
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.upload_dir, exist_ok=True)
        
        print("Loading models... This may take 1-2 minutes on first run...")
        
        self.tone_color_converter = ToneColorConverter(
            config_path=self.config_path,
            device=self.device
        )
        self.tone_color_converter.load_ckpt(self.ckpt_converter)
        
        self.base_speaker_tts = BaseSpeakerTTS(
            config_path=self.config_path,
            device=self.device
        )
        self.base_speaker_tts.load_ckpt(self.ckpt_base)
        
        print("Models loaded successfully!")
        
    def extract_voice_embedding(self, audio_path):
        target_se, _ = se_extractor.get_se(
            audio_path, 
            self.tone_color_converter, 
            vad=False
        )
        return target_se
    
    def synthesize_speech(self, text, voice_embedding, output_path, speed=1.0):
        temp_path = f"{self.output_dir}/temp.wav"
        
        self.base_speaker_tts.tts(
            text=text,
            output_path=temp_path,
            speaker='default',
            language='English',
            speed=speed
        )
        
        self.tone_color_converter.convert(
            audio_src_path=temp_path,
            src_se=None,
            tgt_se=voice_embedding,
            output_path=output_path
        )
        
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return output_path
    
    def synthesize_long_text(self, text_chunks, voice_embedding, output_base_name, speed=1.0):
        audio_segments = []
        
        for i, chunk in enumerate(text_chunks):
            print(f"Processing chunk {i+1}/{len(text_chunks)}...")
            chunk_output = f"{self.output_dir}/temp_chunk_{i}.wav"
            self.synthesize_speech(chunk, voice_embedding, chunk_output, speed)
            
            # Load the audio chunk
            audio, sr = sf.read(chunk_output)
            audio_segments.append(audio)
            
            # Clean up temp file
            os.remove(chunk_output)
        
        # Combine all audio segments
        combined_audio = np.concatenate(audio_segments)
        final_output = f"{self.output_dir}/{output_base_name}.wav"
        sf.write(final_output, combined_audio, sr)
        
        return final_output