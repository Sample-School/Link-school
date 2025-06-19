# Signals para popular dados iniciais automaticamente
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import GrupoEnsino, AnoEscolar


@receiver(post_migrate)
def popula_grupos_anos(sender, **kwargs):
    """
    Popula automaticamente os grupos de ensino e anos escolares após as migrações.
    Executa apenas para a app LSDash para evitar duplicações.
    """
    if sender.name != 'LSDash':  
        return

    # Criação dos grupos de ensino básicos
    fundamental1, _ = GrupoEnsino.objects.get_or_create(nome="Fundamental 1")
    fundamental2, _ = GrupoEnsino.objects.get_or_create(nome="Fundamental 2")
    medio, _ = GrupoEnsino.objects.get_or_create(nome="Ensino Médio")

    # População dos anos do Fundamental 1 (1º ao 5º ano)
    for i in range(1, 6):
        AnoEscolar.objects.get_or_create(
            grupo_ensino=fundamental1, 
            nome=f"{i}º Ano", 
            ordem=i
        )

    # População dos anos do Fundamental 2 (6º ao 9º ano)
    for i in range(6, 10):
        AnoEscolar.objects.get_or_create(
            grupo_ensino=fundamental2, 
            nome=f"{i}º Ano", 
            ordem=i
        )

    # População dos anos do Ensino Médio (1º ao 3º ano)
    for i in range(1, 4):
        AnoEscolar.objects.get_or_create(
            grupo_ensino=medio, 
            nome=f"{i}º Ano", 
            ordem=i
        )