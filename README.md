# Auth App - Railway Deployment

## Deploy na Railway

1. Stwórz repo na GitHub i wypchnij kod:
   ```bash
   git init
   git add .
   git commit -m "Railway deploy"
   git branch -M main
   git remote add origin git@github.com:Uzytkownik/auth_app.git
   git push -u origin main
   ```
2. Zaloguj się na Railway i **New Project → Deploy from GitHub**.
3. Wybierz repo `auth_app`.
4. Dodaj plugin **PostgreSQL** (Railway automatycznie ustawi `DATABASE_URL`).
5. W zakładce **Environment** dodaj zmienne:
   ```
   SECRET_KEY=twoj_secret
   MAIL_USERNAME=twoj_email@gmail.com
   MAIL_PASSWORD=twoje_haslo
   ```
6. Railway wykryje `requirements.txt` i `Procfile`.  
7. Kliknij **Deploy**.  
8. Po chwili aplikacja będzie dostępna pod publicznym URL-em.

## Uruchomienie lokalne

1. Rozpakuj repo i wejdź do katalogu:  
   ```bash
   git clone <repo-url> && cd auth_app
   ```
2. Utwórz wirtualne środowisko i aktywuj:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
3. Zainstaluj zależności:
   ```bash
   pip install -r requirements.txt
   ```
4. Skopiuj `.env.example` do `.env` i uzupełnij dane.
5. Uruchom:
   ```bash
   python app.py
   ```
6. Otwórz `http://127.0.0.1:5000`.