import requests
import os
from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip, AudioFileClip, ImageClip
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from fastapi import FastAPI
from pydantic import BaseModel
import uuid

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "Pomy8i7f1a2K4sMC54l4ExbSxXWK0cYKKsoJsi7djP9ApMSp4qtDKP7U")
PEXELS_URL = "https://api.pexels.com/videos/search"

app = FastAPI()

class ReelRequest(BaseModel):
    topic: str

def download_pexels_videos(query, max_videos=2):
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": max_videos}
    response = requests.get(PEXELS_URL, headers=headers, params=params)

    if response.status_code != 200:
        print("Error fetching videos:", response.text)
        return []

    videos = response.json().get("videos", [])
    file_paths = []
    for i, video in enumerate(videos):
        video_url = video["video_files"][0]["link"]
        file_name = f"video_{i}.mp4"
        with requests.get(video_url, stream=True) as r:
            with open(file_name, "wb") as f:
                f.write(r.content)
        file_paths.append(file_name)
    return file_paths

def create_voiceover(text, filename="voice.mp3"):
    tts = gTTS(text=text, lang="en")
    tts.save(filename)
    return filename

def create_text_image(text, filename="text_overlay.png", size=(1080, 200), fontsize=60):
    img = Image.new("RGBA", size, (0, 0, 0, 150))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", fontsize)
    except:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    position = ((size[0] - text_w) // 2, (size[1] - text_h) // 2)
    draw.text(position, text, font=font, fill=(255, 255, 255, 255))
    img.save(filename)
    return filename

def create_reel(videos, voiceover_text, output_file="final_reel.mp4"):
    clips = []
    for v in videos:
        clip = VideoFileClip(v).resize(height=1920).set_position("center")
        clip = clip.set_duration(5)
        clips.append(clip)

    final_video = concatenate_videoclips(clips, method="compose")
    voice_path = create_voiceover(voiceover_text)
    audio = AudioFileClip(voice_path)
    final_video = final_video.set_audio(audio)
    text_img_path = create_text_image(voiceover_text)
    text_clip = ImageClip(text_img_path).set_duration(final_video.duration).set_position(("center", "bottom"))
    final_video = CompositeVideoClip([final_video, text_clip])
    final_video.write_videofile(output_file, fps=24)
    return output_file

@app.post("/make-reel/")
def make_reel(req: ReelRequest):
    video_files = download_pexels_videos(req.topic)
    if not video_files:
        return {"error": "No videos found"}
    filename = f"reel_{uuid.uuid4()}.mp4"
    text_script = f"This is a reel about {req.topic}. Enjoy watching!"
    output_file = create_reel(video_files, text_script, output_file=filename)
    return {"status": "success", "file": output_file}
