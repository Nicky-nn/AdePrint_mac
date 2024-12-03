import os
import subprocess

def register_scheme():
    plist_path = os.path.join(os.path.dirname(__file__), 'adeprint_live.plist')
    command = f"defaults import com.integrate.adeprint {plist_path}"
    subprocess.run(command, shell=True, check=True)
    print("Esquema registrado correctamente.")

if __name__ == "__main__":
    register_scheme()