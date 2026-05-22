Para executar o projeto, é preciso ter instalado no computador:


* Docker Desktop
* Python



Primeira vez executando:

Setup steps (PostgreSQL + first run)



1\. Install/start PostgreSQL

Download from postgresql.org or use Docker (a senha do banco é postgres):



docker run -d --name pg -e POSTGRES\_PASSWORD=postgres -p 5432:5432 postgres:16



2\. Create the database



psql -U postgres -c "CREATE DATABASE youtube\_curator;"



3\. Fill in .env



DB\_PASSWORD=yourpassword



4\. Install dependencies



pip install -r requirements.txt



5\. Run migrations



python manage.py migrate



6\. Create an admin (optional)



python manage.py createsuperuser



\# then seed their modules:

python manage.py seed\_modules --username <your-admin-username>



7\. Start the server



python manage.py runserver



Open http://127.0.0.1:8000 → click "Criar conta" to register. The 3 training modules are created automatically on registration


Nas outras vezes, rode:

1) Inicialize o docker desktop e depois ative o container com o comando:

docker run -d --name pg -e POSTGRES\_PASSWORD=postgres -p 5432:5432 postgres:16


2) Crie o banco de dados e rode as migrações:



docker exec -it pg psql -U postgres -c "CREATE DATABASE youtube\_curator;"



python manage.py migrate



python manage.py runserver

