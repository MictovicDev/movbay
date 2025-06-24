import socket

try:
    ip = socket.gethostbyname("db.apyejthrfhyflkbihvvx.supabase.co")
    print("✅ Resolved IP:", ip)
except Exception as e:
    print("❌ DNS Resolution Failed:", e)
