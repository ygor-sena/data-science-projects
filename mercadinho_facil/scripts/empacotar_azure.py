"""Gera deploy-azure.zip com o código a ser enviado ao Azure App Service.

Exclui segredos (.env), o ambiente virtual local, testes, caches e os
arquivos específicos da AWS.
Uso (na raiz do projeto):  python scripts/empacotar_azure.py
"""
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "deploy-azure.zip"
PASTAS_EXCLUIDAS = {".venv", "venv", ".git", ".claude", ".pytest_cache", "__pycache__",
                    "tests", "staticfiles", "scripts", ".elasticbeanstalk", ".ebextensions"}
ARQUIVOS_EXCLUIDOS = {".env", ".coverage", ".ebignore", "Procfile",
                      SAIDA.name, "mercadinho-aws.zip"}


def incluir(caminho: Path) -> bool:
    rel = caminho.relative_to(RAIZ)
    if any(parte in PASTAS_EXCLUIDAS for parte in rel.parts[:-1]):
        return False
    return rel.name not in ARQUIVOS_EXCLUIDOS and caminho.suffix != ".pyc"


def main():
    arquivos = sorted(p for p in RAIZ.rglob("*") if p.is_file() and incluir(p))
    with zipfile.ZipFile(SAIDA, "w", zipfile.ZIP_DEFLATED) as zf:
        for arquivo in arquivos:
            zf.write(arquivo, arquivo.relative_to(RAIZ).as_posix())
    print(f"{SAIDA.name} criado com {len(arquivos)} arquivos.")


if __name__ == "__main__":
    main()
