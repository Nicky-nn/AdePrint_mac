import fnmatch
import sys
from urllib.parse import urlparse
import rumps
import multiprocessing
import tkinter as tk
from tkinter import ttk, messagebox
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import tempfile
import platform
import requests
import logging
import cups
import socket
from io import StringIO

# Configurar logging en memoria
log_stream = StringIO()
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler(log_stream)])

# Función para obtener los logs
TOKEN = "eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAiNTkxNzg4MTI1NDgiLCAibmFtZSI6ICJOaWNrIFJ1c3NlbGwiLCAiaWF0IjogMTY4MDMwNzIwMH0.oItFyNgWQlsWHaJ8_fJVyZwEJ0IS9W-d9uBxXJIfqIo"
headers = {"X-Secret-Token": TOKEN}

def get_logs():
    return log_stream.getvalue()


def run_flask():
    app = Flask(__name__)
    CORS(app)  # Habilitar CORS para todas las rutas

    DOMINIOS_PERMITIDOS = [
        "*.integrate.com.bo",
        "*.isipass.net",
        "*.isipay.me",
        "*.idematica.net",
        "*.quickpay.com.bo",
        "*.isipass.com.bo",
    ]


    def dominio_permitido(dominio):
        for permitido in DOMINIOS_PERMITIDOS:
            if fnmatch.fnmatch(dominio, permitido):
                return True
        return False

    @app.before_request
    def verificar_dominio():
        origen = request.headers.get('Origin')
        if origen:
            dominio = urlparse(origen).netloc
            if dominio not in ["localhost", "127.0.0.1"] and not dominio_permitido(dominio):
                return jsonify({"error": "Acceso denegado: dominio no permitido"}), 403
        else:
            # Permitir acceso si la solicitud es local (desde el mismo programa) y tiene el token secreto
            if request.remote_addr in ["127.0.0.1", "::1"]:
                token = request.headers.get('X-Secret-Token')
                if token != TOKEN:
                    return jsonify({"error": "Acceso denegado: token inválido"}), 403
            else:
                return jsonify({"error": "Acceso denegado: origen no permitido"}), 403

    def send_cut_command(printer_name):
        logging.debug(
            f"Enviando comando de corte a la impresora: {printer_name}")
        cut_command = b"\x1D\x56\x00"  # Comando de corte de papel

        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp:
                temp.write(cut_command)
                temp_path = temp.name

            conn = cups.Connection()
            conn.printFile(printer_name, temp_path, "Comando de Corte", {})
            os.remove(temp_path)
            logging.debug("Comando de corte enviado exitosamente")
        except Exception as e:
            logging.error(f"Error al enviar el comando de corte: {str(e)}")
            raise

    def print_pdf(file_path, printer_name):
        logging.debug(f"Intentando imprimir el archivo: {
                      file_path} en la impresora: {printer_name}")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"El archivo {file_path} no existe")

        logging.debug("Usando el sistema de impresión CUPS")
        conn = cups.Connection()
        if printer_name not in conn.getPrinters():
            raise RuntimeError(f"La impresora {printer_name} no se encontró")

        try:
            job_id = conn.printFile(
                printer_name, file_path, "Trabajo de Impresión Python", {})
            logging.debug(
                f"Trabajo de impresión enviado exitosamente. ID del trabajo: {job_id}")
        except Exception as e:
            logging.error(f"Error durante la impresión con CUPS: {str(e)}")
            raise

        # Enviar comando de corte después de imprimir
        try:
            send_cut_command(printer_name)
        except Exception as e:
            logging.error(f"Error al enviar el comando de corte: {str(e)}")

    @app.route('/print', methods=['POST'])
    def print_document():
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        printer_name = request.form.get('printer')
        if not printer_name:
            return jsonify({"error": "No printer specified"}), 400

        # Guardar el archivo temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
            file.save(temp.name)
            temp_path = temp.name

        logging.debug(f"Temporary file saved at: {temp_path}")

        # Imprimir el archivo
        try:
            print_pdf(temp_path, printer_name)
        except Exception as e:
            logging.error(f"Error during printing: {str(e)}")
            return jsonify({"error": f"Error printing: {str(e)}"}), 500
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logging.debug(f"Temporary file removed: {temp_path}")
            else:
                logging.warning(
                    f"Temporary file not found for removal: {temp_path}")

        return jsonify({"message": "Printing started"}), 200

    @app.route('/printPDF', methods=['POST'])
    def print_pdfURL():
        data = request.get_json()
        pdf_url = data.get('pdf_url')
        printer_name = data.get('printer')

        if not pdf_url:
            return jsonify({"error": "No se ha proporcionado la URL del PDF"}), 400

        if not printer_name:
            return jsonify({"error": "No se ha especificado una impresora"}), 400

        # Descargar el archivo PDF de la URL
        try:
            response = requests.get(pdf_url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to download PDF: {str(e)}")
            return jsonify({"error": f"Failed to download PDF: {str(e)}"}), 400

        # Guardar el archivo temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
            temp.write(response.content)
            temp_path = temp.name

        logging.debug(f"Temporary file saved at: {temp_path}")

        # Imprimir el archivo
        try:
            print_pdf(temp_path, printer_name)
        except Exception as e:
            logging.error(f"Error during printing: {str(e)}")
            return jsonify({"error": f"Error printing PDF: {str(e)}"}), 500
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logging.debug(f"Temporary file removed: {temp_path}")
            else:
                logging.warning(
                    f"Temporary file not found for removal: {temp_path}")

        return jsonify({"message": "Se ha iniciado la impresión del PDF"}), 200

    @app.route('/printers', methods=['GET'])
    def get_printers():
        conn = cups.Connection()
        printers = list(conn.getPrinters().keys())
        if platform.system() == "Darwin":  # macOS
            printers = [printer for printer in printers if 'inactive' not in conn.getPrinterAttributes(printer)[
                'printer-state-message']]

        return jsonify({"printers": printers}), 200

    @app.route('/print_jobs', methods=['GET'])
    def get_print_jobs():
        print("Getting print jobs")
        conn = cups.Connection()
        jobs = conn.getJobs()
        job_list = []
        for job_id, job in jobs.items():
            job_list.append({
                "id": job_id,
                "title": job["job-name"],
                "user": job["job-originating-user-name"],
                "printer": job["printer-uri"],
                "status": job["job-state"]
            })
        return jsonify({"jobs": job_list}), 200

    @app.route('/clear_jobs', methods=['DELETE'])
    def clear_print_jobs():
        conn = cups.Connection()
        jobs = conn.getJobs()
        for job_id in jobs.keys():
            try:
                conn.cancelJob(job_id)
            except Exception as e:
                logging.error(f"Error al cancelar el trabajo de impresión {
                              job_id}: {str(e)}")
                return jsonify({"error": f"Error al cancelar el trabajo de impresión {job_id}: {str(e)}"}), 500
        return jsonify({"message": "Todos los trabajos de impresión en cola han sido cancelados"}), 200

    app.run(host='0.0.0.0', port=7777, use_reloader=False)


def run_gui():
    def on_closing():
        root.destroy()

    def imprimir_prueba():
        try:
            printer = selected_printer.get()
            if not printer:
                messagebox.showwarning(
                    "Advertencia", "Seleccione una impresora antes de intentar imprimir.")
                return
            file_path = os.path.join(os.path.dirname(__file__), 'static/pdf/prueba.pdf')
            files = {'file': open(file_path, 'rb')}
            data = {'printer': printer}
            response = requests.post(
                'http://localhost:7777/print', files=files, data=data, headers=headers)
            response.raise_for_status()
            messagebox.showinfo("Éxito", "La impresión de prueba ha comenzado")
        except FileNotFoundError:
            logging.error("El archivo de prueba no se encontró.")
            messagebox.showerror(
                "Error", "El archivo de prueba no se encontró'.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al imprimir prueba: {str(e)}")
            messagebox.showerror(
                "Error", f"Error al imprimir prueba: {str(e)}")

    def listar_impresoras():
        try:
            response = requests.get(
                'http://localhost:7777/printers', headers={'X-Secret-Token': TOKEN})
            response.raise_for_status()
            printers = response.json().get('printers', [])
            return printers
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al listar impresoras: {str(e)}")
            return []

    def listar_historial():
        try:
            response = requests.get('http://localhost:7777/print_jobs', headers=headers)
            response.raise_for_status()
            jobs = response.json().get('jobs', [])
            return jobs
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al listar historial: {str(e)}")
            return []

    def borrar_cola():
        try:
            response = requests.delete('http://localhost:7777/clear_jobs', headers=headers)
            response.raise_for_status()
            messagebox.showinfo(
                "Éxito", "Todos los trabajos de impresión en cola han sido cancelados")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al borrar cola: {str(e)}")
            messagebox.showerror("Error", f"Error al borrar cola: {str(e)}")

    def actualizar_impresoras():
        impresoras_combobox['values'] = []
        impresoras_combobox.set('')
        printers = listar_impresoras()
        if printers:
            impresoras_combobox['values'] = printers
        else:
            messagebox.showwarning(
                "Advertencia", "No se encontraron impresoras.")

    def actualizar_logs():
        logs_text.delete(1.0, tk.END)
        logs_text.insert(tk.END, get_logs())

    # Crear la ventana principal
    root = tk.Tk()
    root.title("Interfaz de Servicios de Impresión")

    # Manejar el cierre de la aplicación
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Crear el notebook (pestañas)
    notebook = ttk.Notebook(root)
    notebook.pack(pady=10, expand=True)

    def actualizar_pestañas(event):
        selected_tab = event.widget.tab(event.widget.select(), "text")
        if selected_tab == "Impresoras":
            actualizar_impresoras()
        elif selected_tab == "Logs":
            actualizar_logs()

    notebook.bind("<<NotebookTabChanged>>", actualizar_pestañas)

    # --- Pestaña de Cuenta ---
    cuenta_frame = ttk.Frame(notebook, width=400, height=280)
    cuenta_frame.pack(fill='both', expand=True)
    ttk.Label(cuenta_frame, text="Bienvenido a AdePrint",
              font=("Helvetica", 16)).pack(pady=10)
    # Agregar link a la página web o hipervínculo
    ttk.Label(cuenta_frame, text="Disfruta de nuestro servicio de impresión en línea, rápido y seguro.").pack(pady=5)
    ttk.Button(cuenta_frame, text="Ayuda", command=lambda: messagebox.showinfo(
        "Ayuda", "Para más información, visita https://integrate.com.bo/impresoras")).pack(pady=5)
    ttk.Button(cuenta_frame, text="Salir", command=on_closing).pack(pady=5)

    # --- Pestaña de Impresoras ---
    impresoras_frame = ttk.Frame(notebook, width=400, height=280)
    impresoras_frame.pack(fill='both', expand=True)
    ttk.Label(impresoras_frame, text="Impresoras Instaladas",
              font=("Helvetica", 16)).pack(pady=10)

    # Crear un Combobox para listar impresoras
    selected_printer = tk.StringVar()
    impresoras_combobox = ttk.Combobox(
        impresoras_frame, textvariable=selected_printer, state="readonly")
    impresoras_combobox.pack(pady=5, fill='x', padx=20)

    # Botón de Probar Impresión habilitado solo cuando se selecciona una impresora
    probar_imprimir_button = ttk.Button(
        impresoras_frame, text="Probar Impresión", command=imprimir_prueba, state="disabled")
    probar_imprimir_button.pack(pady=5)

    def on_printer_select(event):
        if selected_printer.get():
            probar_imprimir_button.config(state="normal")
        else:
            probar_imprimir_button.config(state="disabled")

    impresoras_combobox.bind("<<ComboboxSelected>>", on_printer_select)

    # --- Pestaña de Logs ---
    logs_frame = ttk.Frame(notebook, width=400, height=280)
    logs_frame.pack(fill='both', expand=True)
    ttk.Label(logs_frame, text="Logs del Sistema",
              font=("Helvetica", 16)).pack(pady=10)
    logs_text = tk.Text(logs_frame, wrap='word')
    logs_text.pack(pady=5, fill='both', expand=True)

    # Añadir las pestañas al notebook
    notebook.add(cuenta_frame, text='Cuenta')
    notebook.add(impresoras_frame, text='Impresoras')
    notebook.add(logs_frame, text='Logs')

    root.after(5000, actualizar_logs)

    root.mainloop()


class TrayApp(rumps.App):
    def __init__(self):
        super(TrayApp, self).__init__("Servicio de Impresión",
                                      icon="static/favicon.ico", quit_button=None)
        self.menu = ["Abrir GUI", "Probar Impresión", "Ver Impresoras",
                     "Ver Historial", "Borrar Cola", None, "Salir"]
        self.flask_process = None
        self.gui_process = None

    @rumps.clicked("Abrir GUI")
    def abrir_gui(self, _):
        if self.gui_process is None or not self.gui_process.is_alive():
            self.gui_process = multiprocessing.Process(target=run_gui)
            self.gui_process.start()
        else:
            rumps.notification("Servicio de Impresión",
                               "Información", "La GUI ya está abierta.")

    @rumps.clicked("Probar Impresión")
    def test_print(self, _):
        try:
            printers = listar_impresoras_tray()
            if not printers:
                rumps.alert(
                    title="Error", message="No se encontraron impresoras disponibles.")
                return
            # Seleccionar la primera impresora por defecto
            selected_printer = printers[0]
            file_path = os.path.join(os.path.dirname(__file__), 'static/pdf/prueba.pdf')
            files = {'file': open(file_path, 'rb')}
            data = {'printer': selected_printer}
            response = requests.post(
                'http://localhost:7777/print', files=files, data=data, headers=headers)
            response.raise_for_status()
            rumps.notification("Servicio de Impresión", "Éxito",
                               "La impresión de prueba ha comenzado")
        except FileNotFoundError:
            logging.error("El archivo de prueba no se encontró.")
            rumps.alert(
                title="Error", message="El archivo de prueba no se encontró.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al imprimir prueba: {str(e)}")
            rumps.alert(title="Error",
                        message=f"Error al imprimir prueba: {str(e)}")

    @rumps.clicked("Ver Impresoras")
    def show_printers(self, _):
        printers = listar_impresoras_tray()
        if printers:
            printer_list = "\n".join(printers)
            rumps.alert(title="Impresoras Instaladas", message=printer_list)
        else:
            rumps.alert(title="Impresoras Instaladas",
                        message="No se encontraron impresoras.")

    @rumps.clicked("Ver Historial")
    def show_history(self, _):
        try:
            response = requests.get('http://localhost:7777/print_jobs', headers=headers)
            response.raise_for_status()
            jobs = response.json().get('jobs', [])
            if jobs:
                job_list = ""
                for job in jobs:
                    job_list += f"ID: {job['id']}, Título: {job['title']
                                                            }, Estado: {job['status']}\n"
            else:
                job_list = "No hay trabajos en el historial."
            rumps.alert(title="Historial de Impresiones", message=job_list)
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al listar historial: {str(e)}")
            rumps.alert(title="Error",
                        message=f"Error al listar historial: {str(e)}")

    @rumps.clicked("Borrar Cola")
    def clear_queue(self, _):
        try:
            response = requests.delete('http://localhost:7777/clear_jobs', headers=headers)
            response.raise_for_status()
            rumps.notification("Servicio de Impresión", "Éxito",
                               "Todos los trabajos de impresión en cola han sido cancelados")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error al borrar cola: {str(e)}")
            rumps.alert(title="Error",
                        message=f"Error al borrar cola: {str(e)}")

    @rumps.clicked("Salir")
    def quit_app(self, _):
        try:
            if self.flask_process and self.flask_process.is_alive():
                self.flask_process.terminate()
            if self.gui_process and self.gui_process.is_alive():
                self.gui_process.terminate()
        except Exception as e:
            logging.error(f"Error al terminar procesos: {str(e)}")
        rumps.quit_application()


def check_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def listar_impresoras_tray():
    try:
        response = requests.get('http://localhost:7777/printers', headers={'X-Secret-Token': TOKEN})
        response.raise_for_status()
        printers = response.json().get('printers', [])
        return printers
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al listar impresoras: {str(e)}")
        return []


def main():
    # Verificar si el puerto 7777 está en uso
    if check_port_in_use(7777):
        logging.error(
            "El puerto 7777 ya está en uso. Por favor, elija otro puerto.")
        rumps.alert(title="Error", message="El puerto 7777 ya está en uso. Por favor, cierre la aplicación que está utilizando el puerto o use otro puerto.")
        sys.exit(1)
    else:
        # Iniciar el servidor Flask en un proceso separado
        flask_process = multiprocessing.Process(target=run_flask)
        flask_process.daemon = True
        flask_process.start()

    # Iniciar la aplicación de bandeja con rumps
    tray = TrayApp()
    tray.flask_process = flask_process
    tray.run()


if __name__ == "__main__":
    # Establecer el método de inicio (opcional)
    # multiprocessing.set_start_method('fork')

    multiprocessing.freeze_support()
    main()
