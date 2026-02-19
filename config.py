import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(BASE_DIR, "data", "jerry_outreach.db")
UPLOAD_FOLDER_FLYERS = os.path.join(BASE_DIR, "uploads", "flyers")
UPLOAD_FOLDER_CSV = os.path.join(BASE_DIR, "uploads", "csv")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-jerry-nonqm-secret-key")
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}
ALLOWED_CSV_EXTENSIONS = {"csv", "xlsx"}
