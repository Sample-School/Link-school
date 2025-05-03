from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import GrupoEnsino, AnoEscolar

@receiver(post_migrate)
def popula_grupos_anos(sender, **kwargs):
    if sender.name != 'LSDash':  
        return

    # Grupos de ensino
    fundamental1, _ = GrupoEnsino.objects.get_or_create(nome="Fundamental 1")
    fundamental2, _ = GrupoEnsino.objects.get_or_create(nome="Fundamental 2")
    medio, _ = GrupoEnsino.objects.get_or_create(nome="Ensino Médio")

    # Anos escolares
    for i in range(1, 6):
        AnoEscolar.objects.get_or_create(grupo_ensino=fundamental1, nome=f"{i}º Ano", ordem=i)

    for i in range(6, 10):
        AnoEscolar.objects.get_or_create(grupo_ensino=fundamental2, nome=f"{i}º Ano", ordem=i)

    for i in range(1, 4):
        AnoEscolar.objects.get_or_create(grupo_ensino=medio, nome=f"{i}º Ano", ordem=i)
