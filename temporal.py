import base64
import json
import secrets
import hmac
import hashlib

def base64_url_encode(data: bytes) -> str:
    """
    Codifica datos en Base64 URL Safe.
    
    Args:
        data (bytes): Datos a codificar.
    
    Returns:
        str: Cadena codificada en Base64 URL Safe.
    """
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def generar_token_jwt(claims: dict, secret_key: str = "mi_clave_secreta") -> str:
    """
    Genera un token estilo JWT con un header, payload y firma.
    
    Args:
        claims (dict): Datos (payload) a incluir en el token.
        secret_key (str): Clave secreta para la firma.
    
    Returns:
        str: Token generado.
    """
    # Header
    header = {
        "alg": "HS256",  # HMAC con SHA-256
        "typ": "JWT"
    }
    encoded_header = base64_url_encode(json.dumps(header).encode('utf-8'))
    
    # Payload
    encoded_payload = base64_url_encode(json.dumps(claims).encode('utf-8'))
    
    # Firma (Signature)
    signature_input = f"{encoded_header}.{encoded_payload}".encode('utf-8')
    signature = hmac.new(secret_key.encode('utf-8'), signature_input, hashlib.sha256).digest()
    encoded_signature = base64_url_encode(signature)
    
    # Token final
    jwt_token = f"{encoded_header}.{encoded_payload}.{encoded_signature}"
    return jwt_token

if __name__ == "__main__":
    print("Generador de Tokens estilo JWT")
    # Payload de ejemplo
    payload = {
        "sub": "59178812548",
        "name": "Nick Russell",
        "iat": 1680307200  # Ejemplo de 'issued at' (timestamp)
    }
    secret = input("Ingresa tu clave secreta (opcional, presiona Enter para usar una por defecto): ") or "mi_clave_secreta"
    token = generar_token_jwt(payload, secret)
    print("\nToken generado:")
    print(token)
