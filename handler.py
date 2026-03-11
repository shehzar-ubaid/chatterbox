import sys
import os
import traceback
import base64

# Worker start honay ka pehla saboot
print("1. Container started, starting Infinity Clone worker...")
sys.stdout.flush()

# RunPod Import Check
try:
    import runpod
    print("2. RunPod library successfully imported.")
except Exception as e:
    print(f"CRITICAL ERROR: RunPod import fail ho gaya: {e}")
    sys.exit(1)

# Source folder path add kiya
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Asli Model Load Karein
model = None
try:
    print("3. Model load ho raha hai...")
    
    # Yahan humne asli model ko on kar diya hay
    from chatterbox import Chatterbox 
    model = Chatterbox.load_model("./models")
    
    print("4. Model VRAM mein load ho gaya!")
except Exception as e:
    print("ERROR: Model load hotay waqt masla aya:")
    print(traceback.format_exc())

def process_audio(job):
    job_input = job.get('input', {})
    text = job_input.get('text', 'Hello from Infinity Clone')
    voice_id = job_input.get('voice_id', 'default_voice')
    
    try:
        print(f"Processing job ID: {job.get('id')}")
        
        if model is None:
             return {"error": "API failed. Model theek say load nahi hua."}
        
        # Real generation code on kar diya
        audio_path = model.synthesize(text=text, voice=voice_id)
        
        with open(audio_path, "rb") as audio_file:
            audio_base64 = base64.b64encode(audio_file.read()).decode('utf-8')

        return {
            "status": "success",
            "audio_base64": audio_base64
        }
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

print("5. Starting RunPod Serverless handler...")
sys.stdout.flush()
runpod.serverless.start({"handler": process_audio})