import cloudinary
import cloudinary.uploader
import tempfile
import cv2
import os

cloudinary.config(
    cloud_name="dlpjswzj0",
    api_key="787633141853545",
    api_secret="XrRKeRsNpIhv-JWrJEx7C5jt2bM"
)

def upload_clip_to_cloudinary(frames, fps, clip_id):
    fd, temp_path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)

    height, width, _ = frames[0].shape
    writer = cv2.VideoWriter(temp_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    for f in frames:
        writer.write(f)
    writer.release()

    response = cloudinary.uploader.upload(temp_path, resource_type="video",
                                          public_id=f"accident_{clip_id}", folder="FYP")

    os.remove(temp_path)
    return response.get('secure_url')
