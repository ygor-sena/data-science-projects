DEFAULT_MODULES = [
    {
        "name": "Conhecimento do Produto",
        "slug": "conhecimento-produto",
        "description": (
            "Aprenda sobre os produtos mineiros: queijos artesanais, doces de leite, "
            "cachaças e outros itens típicos. Entenda qualidade, armazenamento e valor agregado."
        ),
        "default_keywords": "queijo mineiro artesanal,doce de leite,cachaça artesanal,produtos típicos minas gerais",
        "icon": "bi-box-seam",
    },
    {
        "name": "Técnicas de Venda",
        "slug": "tecnicas-venda",
        "description": (
            "Desenvolva habilidades de abordagem ao cliente, argumentação de valor, "
            "como lidar com objeções e conduzir uma venda de sucesso."
        ),
        "default_keywords": "técnicas de venda,como vender mais,argumentação de vendas,objeções de clientes",
        "icon": "bi-graph-up-arrow",
    },
    {
        "name": "Atendimento ao Cliente",
        "slug": "atendimento-cliente",
        "description": (
            "Melhore a postura no atendimento, pratique escuta ativa e aprenda a "
            "resolver problemas com excelência, fidelizando clientes."
        ),
        "default_keywords": "atendimento ao cliente,escuta ativa,excelência no atendimento,fidelização de clientes",
        "icon": "bi-people",
    },
]


def seed_user_modules(user):
    from curator.models import TrainingModule

    for data in DEFAULT_MODULES:
        TrainingModule.objects.get_or_create(
            slug=data["slug"],
            created_by=user,
            defaults=data,
        )
