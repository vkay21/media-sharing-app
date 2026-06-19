from flask import Flask, render_template, request, redirect, url_for
import os
import uuid
from datetime import datetime
from PIL import Image

app = Flask(__name__)

IMAGE_FOLDER = "static/images"
THUMBNAIL_FOLDER = "static/thumbnails"
images = []
os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)


@app.route("/")
def home():
    return render_template("index.html", images=images)


@app.route("/upload", methods=["POST"])
def upload():
    title = request.form.get("title")
    description = request.form.get("description")
    tags = request.form.get("tags")
    file = request.files.get("image")

    if not file or file.filename == "":
        return redirect(url_for("home"))

    image_id = str(uuid.uuid4())
    filename = f"{image_id}-{file.filename}"

    image_path = os.path.join(IMAGE_FOLDER, filename)
    thumbnail_path = os.path.join(THUMBNAIL_FOLDER, filename)

    file.save(image_path)

    img = Image.open(image_path)
    img.thumbnail((120, 120))
    img.save(thumbnail_path)

    images.append({
        "image_id": image_id,
        "title": title,
        "description": description,
        "tags": tags,
        "filename": file.filename,
        "image_url": "/" + image_path,
        "thumbnail_url": "/" + thumbnail_path,
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    return redirect(url_for("home"))


@app.route("/delete/<image_id>", methods=["POST"])
def delete(image_id):
    global images

    selected_image = None

    for image in images:
        if image["image_id"] == image_id:
            selected_image = image
            break

    if selected_image:
        image_path = selected_image["image_url"].replace("/", "", 1)
        thumbnail_path = selected_image["thumbnail_url"].replace("/", "", 1)

        if os.path.exists(image_path):
            os.remove(image_path)

        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)

        images = [image for image in images if image["image_id"] != image_id]

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)