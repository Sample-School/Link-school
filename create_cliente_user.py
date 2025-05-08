import os
import django
import argparse

# Configurar o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LSmain.settings')
django.setup()

from django_tenants.utils import schema_context
from django.contrib.auth.hashers import make_password
from LSCliente.models import UsuarioCliente


def criar_usuario(schema, email, senha, nome):
    try:
        with schema_context(schema):
            if UsuarioCliente.objects.filter(email=email).exists():
                print(f"⚠️ Usuário com email {email} já existe no schema '{schema}'")
                return

            user = UsuarioCliente.objects.create(
                email=email,
                nome=nome,
                password=make_password(senha),  # 👈 aqui está o segredo
                is_active=True,
                is_master=False,
                is_staff=False,
                is_superuser=False
            )

            print(f"✅ Usuário '{user.email}' criado com sucesso no schema '{schema}'")

    except Exception as e:
        print(f"❌ Erro ao criar usuário: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cria um usuário no tenant cliente")
    parser.add_argument('--schema', type=str, required=True, help="Nome do schema do cliente")
    parser.add_argument('--email', type=str, required=True, help="Email do usuário")
    parser.add_argument('--senha', type=str, required=True, help="Senha do usuário")
    parser.add_argument('--nome', type=str, required=True, help="Nome completo do usuário")

    args = parser.parse_args()

    criar_usuario(
        schema=args.schema,
        email=args.email,
        senha=args.senha,
        nome=args.nome
    )
