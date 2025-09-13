from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.models import TTSRequest, PDFToSpeechRequest
from app.voice_processor import VoiceProcessor
from app.pdf_processor import PDFProcessor
import os
import uuid
import shutil

app = FastAPI(title="OpenVoice PDF to Speech API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Initializing Voice Processor...")
processor = VoiceProcessor()
voice_embeddings = {}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "device": processor.device}

@app.post("/upload-voice")
async def upload_voice(
    voice_name: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload a voice sample for cloning"""
    if not file.filename.endswith(('.wav', '.mp3')):
        raise HTTPException(status_code=400, detail="Please upload a WAV or MP3 file")
    
    file_path = f"{processor.upload_dir}/{voice_name}_{uuid.uuid4().hex[:8]}.wav"
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    try:
        print(f"Extracting voice embedding for {voice_name}...")
        embedding = processor.extract_voice_embedding(file_path)
        voice_embeddings[voice_name] = {
            "embedding": embedding,
            "file_path": file_path
        }
        return {"voice_id": voice_name, "status": "uploaded", "message": f"Voice '{voice_name}' uploaded successfully"}
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Failed to process voice: {str(e)}")

@app.post("/pdf-to-speech")
async def pdf_to_speech(
    voice_id: str = Form(...),
    speed: float = Form(1.0),
    max_chars: int = Form(5000),
    pdf_file: UploadFile = File(...)
):
    """Convert PDF text to speech using a cloned voice"""
    
    # Check if voice exists
    if voice_id not in voice_embeddings:
        raise HTTPException(
            status_code=404, 
            detail=f"Voice '{voice_id}' not found. Please upload a voice sample first."
        )
    
    # Check file type
    if not pdf_file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Please upload a PDF file")
    
    # Save PDF temporarily
    pdf_path = f"pdfs/temp_{uuid.uuid4().hex[:8]}.pdf"
    os.makedirs("pdfs", exist_ok=True)
    
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(pdf_file.file, f)
    
    try:
        # Extract text from PDF
        print(f"Extracting text from PDF: {pdf_file.filename}")
        text = PDFProcessor.extract_text(pdf_path, max_chars=max_chars)
        
        if not text:
            raise HTTPException(status_code=400, detail="No text could be extracted from the PDF")
        
        print(f"Extracted {len(text)} characters from PDF")
        
        # Split text into chunks
        chunks = PDFProcessor.split_into_chunks(text, chunk_size=500)
        print(f"Split text into {len(chunks)} chunks")
        
        # Generate speech
        voice_data = voice_embeddings[voice_id]
        output_name = f"pdf_speech_{uuid.uuid4().hex[:8]}"
        
        if len(chunks) == 1:
            # Single chunk - direct synthesis
            output_path = f"{processor.output_dir}/{output_name}.wav"
            processor.synthesize_speech(
                chunks[0],
                voice_data["embedding"],
                output_path,
                speed
            )
        else:
            # Multiple chunks - combine
            output_path = processor.synthesize_long_text(
                chunks,
                voice_data["embedding"],
                output_name,
                speed
            )
        
        return FileResponse(
            output_path,
            media_type="audio/wav",
            filename=f"{output_name}.wav",
            headers={
                "X-Text-Length": str(len(text)),
                "X-Chunks-Processed": str(len(chunks))
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        # Clean up PDF file
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

@app.post("/simple-pdf-to-speech")
async def simple_pdf_to_speech(
    pdf_file: UploadFile = File(...),
    voice_file: UploadFile = File(...)
):
    """One-shot PDF to speech: upload both PDF and voice sample"""
    
    # Save voice file
    voice_path = f"{processor.upload_dir}/temp_voice_{uuid.uuid4().hex[:8]}.wav"
    with open(voice_path, "wb") as f:
        shutil.copyfileobj(voice_file.file, f)
    
    # Save PDF file
    pdf_path = f"pdfs/temp_{uuid.uuid4().hex[:8]}.pdf"
    os.makedirs("pdfs", exist_ok=True)
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(pdf_file.file, f)
    
    try:
        # Extract voice embedding
        print("Extracting voice characteristics...")
        voice_embedding = processor.extract_voice_embedding(voice_path)
        
        # Extract PDF text
        print("Extracting PDF text...")
        text = PDFProcessor.extract_text(pdf_path, max_chars=5000)
        
        if not text:
            raise HTTPException(status_code=400, detail="No text found in PDF")
        
        # Generate speech
        print(f"Generating speech for {len(text)} characters...")
        output_name = f"pdf_speech_{uuid.uuid4().hex[:8]}"
        output_path = f"{processor.output_dir}/{output_name}.wav"
        
        processor.synthesize_speech(
            text,
            voice_embedding,
            output_path,
            speed=1.0
        )
        
        return FileResponse(
            output_path,
            media_type="audio/wav",
            filename=f"{output_name}.wav"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp files
        for path in [voice_path, pdf_path]:
            if os.path.exists(path):
                os.remove(path)

@app.get("/voices")
async def list_voices():
    """List all uploaded voices"""
    return {"voices": list(voice_embeddings.keys())}

@app.delete("/voice/{voice_id}")
async def delete_voice(voice_id: str):
    """Delete an uploaded voice"""
    if voice_id not in voice_embeddings:
        raise HTTPException(status_code=404, detail="Voice not found")
    
    voice_data = voice_embeddings.pop(voice_id)
    if os.path.exists(voice_data["file_path"]):
        os.remove(voice_data["file_path"])
    
    return {"status": "deleted", "voice_id": voice_id}