from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os, sys
from utils import process_report_batch

# Detecta caminho base (normal ou dentro do .exe gerado pelo PyInstaller)
def _base_path():
    if hasattr(sys, "_MEIPASS"):  # quando rodar empacotado
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = _base_path()

# Agora o Flask acha templates e static em ambos os casos
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_PATH, "templates"),
    static_folder=os.path.join(BASE_PATH, "static"),
)
app.secret_key = "change-this-key"

# Pasta de uploads: gravável mesmo dentro do exe (usa cwd)
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {".xlsx"}


def allowed_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        files = request.files.getlist("files")
        if not files or len(files) == 0:
            flash("Envie os 10 arquivos .xlsx (5 da semana anterior e 5 da semana atual).")
            return redirect(url_for("index"))

        xlsx_files = [f for f in files if f and allowed_file(f.filename)]
        if len(xlsx_files) == 0:
            flash("Nenhum arquivo .xlsx válido encontrado.")
            return redirect(url_for("index"))

        saved = []
        try:
            for f in xlsx_files:
                original_name = f.filename  # nome original
                filename = secure_filename(original_name)
                path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                f.save(path)
                saved.append({"path": path, "name": original_name})

            resultado = process_report_batch(saved)

        except Exception as e:
            flash(f"Erro ao processar arquivos: {e}")
            resultado = {}

        # Limpa os uploads temporários
        for item in saved:
            try:
                os.remove(item["path"])
            except Exception:
                pass

        return render_template("index.html", resultado=resultado)

    return render_template("index.html", resultado=None)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)