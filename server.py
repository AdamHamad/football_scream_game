import http.server, ssl, os, subprocess, sys

DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 3457
CERT = os.path.join(DIR, 'cert.pem')
KEY = os.path.join(DIR, 'key.pem')

# Generate self-signed cert using Python
if not os.path.exists(CERT) or not os.path.exists(KEY):
    print("Generating self-signed certificate with Python...")
    gen_script = '''
import datetime
try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, u"localhost")])
    cert = (x509.CertificateBuilder()
        .subject_name(subject).issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.IPAddress(import_module("ipaddress").IPv4Address("192.168.1.105")),
            x509.IPAddress(import_module("ipaddress").IPv4Address("0.0.0.0")),
        ]), critical=False)
        .sign(key, hashes.SHA256()))

    with open("''' + CERT.replace('\\','\\\\') + '''", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open("''' + KEY.replace('\\','\\\\') + '''", "wb") as f:
        f.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
    print("CERT_OK")
except Exception as e:
    print("CERT_FAIL:" + str(e))
'''
    # Try cryptography library first
    result = subprocess.run([sys.executable, '-c', gen_script.replace('import_module', '__import__("importlib").import_module')], capture_output=True, text=True)
    if 'CERT_OK' not in result.stdout:
        print("cryptography library not available, trying pip install...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'cryptography', '-q'], capture_output=True)
        result = subprocess.run([sys.executable, '-c', gen_script.replace('import_module', '__import__("importlib").import_module')], capture_output=True, text=True)
        if 'CERT_OK' not in result.stdout:
            print("Cannot generate cert. Falling back to HTTP (mic works on localhost only).")
            print(result.stdout, result.stderr)
            # Fallback: plain HTTP on 0.0.0.0
            os.chdir(DIR)
            handler = http.server.SimpleHTTPRequestHandler
            httpd = http.server.HTTPServer(('0.0.0.0', PORT), handler)
            print(f"\n{'='*50}")
            print(f"  HTTP Server (no HTTPS) on port {PORT}")
            print(f"  Computer: http://localhost:{PORT}")
            print(f"  Phone:    http://192.168.1.105:{PORT}")
            print(f"  ⚠️  Mic may not work on phone without HTTPS")
            print(f"{'='*50}\n")
            httpd.serve_forever()
            sys.exit(0)

os.chdir(DIR)
handler = http.server.SimpleHTTPRequestHandler
httpd = http.server.HTTPServer(('0.0.0.0', PORT), handler)

try:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(CERT, KEY)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    proto = "HTTPS"
except Exception as e:
    print(f"SSL failed ({e}), falling back to HTTP")
    proto = "HTTP"

print(f"\n{'='*50}")
print(f"  {proto} Server running on port {PORT}")
print(f"  Computer:  {proto.lower()}://localhost:{PORT}")
print(f"  Phone:     {proto.lower()}://192.168.1.105:{PORT}")
if proto == "HTTP":
    print(f"  ⚠️  Mic may not work on phone without HTTPS")
print(f"{'='*50}\n")

httpd.serve_forever()
