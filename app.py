from flask import Flask, render_template, request, redirect, url_for
import boto3
import os
import uuid
from datetime import datetime
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "snap-media-bucket-7944")
TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "Data_image")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

LOCAL_IMAGE_FOLDER = "static/images"
LOCAL_THUMBNAIL_FOLDER = "static/thumbnails"

os.makedirs(LOCAL_IMAGE_FOLDER, exist_ok=True)
os.makedirs(LOCAL_THUMBNAIL_FOLDER, exist_ok=True)

s3 = boto3.client("s3", region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)


@app.route("/")
def home():
    try:
        response = table.scan()
        images = response.get("Items", [])
    except Exception as error:
        print("DynamoDB scan error:", error)
        images = []

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
    original_filename = file.filename

    image_key = f"images/{image_id}-{original_filename}"
    thumbnail_key = f"thumbnails/{image_id}-{original_filename}"

    local_image_path = os.path.join(
        LOCAL_IMAGE_FOLDER,
        f"{image_id}-{original_filename}"
    )

    local_thumbnail_path = os.path.join(
        LOCAL_THUMBNAIL_FOLDER,
        f"{image_id}-{original_filename}"
    )

    file.save(local_image_path)

    img = Image.open(local_image_path)
    img.thumbnail((120, 120))
    img.save(local_thumbnail_path)

    try:
        s3.upload_file(
            local_image_path,
            BUCKET_NAME,
            image_key,
            ExtraArgs={"ContentType": file.content_type}
        )

        s3.upload_file(
            local_thumbnail_path,
            BUCKET_NAME,
            thumbnail_key,
            ExtraArgs={"ContentType": file.content_type}
        )

        image_url = f"https://{BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{image_key}"
        thumbnail_url = f"https://{BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{thumbnail_key}"

        table.put_item(
            Item={
                "image_id": image_id,
                "title": title,
                "description": description,
                "tags": tags,
                "filename": original_filename,
                "image_key": image_key,
                "thumbnail_key": thumbnail_key,
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        )

        print("Upload successful:", image_id)

    except Exception as error:
        print("Upload error:", error)

    return redirect(url_for("home"))


@app.route("/delete/<image_id>", methods=["POST"])
def delete(image_id):
    try:
        response = table.get_item(Key={"image_id": image_id})
        image = response.get("Item")

        if image:
            s3.delete_object(
                Bucket=BUCKET_NAME,
                Key=image["image_key"]
            )

            s3.delete_object(
                Bucket=BUCKET_NAME,
                Key=image["thumbnail_key"]
            )

            table.delete_item(
                Key={"image_id": image_id}
            )

            print("Deleted:", image_id)

    except Exception as error:
        print("Delete error:", error)

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)