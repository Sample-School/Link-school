
import requests
from django.db import connection
from django_tenants.utils import schema_context

class QuestaoService:
    """Serviço para buscar questões do schema público (Dashboard)"""
    
    @staticmethod
    def buscar_questoes_dashboard():
        """Busca todas as questões disponíveis no dashboard"""
        with schema_context('public'):
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        q.id,
                        q.titulo,
                        q.tipo,
                        m.nome as materia_nome,
                        ae.nome as ano_escolar,
                        ge.nome as grupo_ensino,
                        uc.username as criado_por
                    FROM "LSDash_questao" q
                    LEFT JOIN "LSDash_materia" m ON q.materia_id = m.id
                    LEFT JOIN "LSDash_anoescolar" ae ON q.ano_escolar_id = ae.id
                    LEFT JOIN "LSDash_grupoensino" ge ON ae.grupo_ensino_id = ge.id
                    LEFT JOIN "LSDash_usermodel" uc ON q.criado_por_id = uc.user_id
                    ORDER BY q.data_criacao DESC
                """)
                
                questoes = []
                for row in cursor.fetchall():
                    questoes.append({
                        'id': row[0],
                        'titulo': row[1],
                        'tipo': row[2],
                        'materia': row[3],
                        'ano_escolar': row[4],
                        'grupo_ensino': row[5],
                        'criado_por': row[6]
                    })
                
                return questoes
    
    @staticmethod
    def buscar_questao_completa(questao_id):
        """Busca uma questão específica com todos os dados"""
        with schema_context('public'):
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        q.id,
                        q.titulo,
                        q.tipo,
                        m.nome as materia_nome,
                        ae.nome as ano_escolar
                    FROM "LSDash_questao" q
                    LEFT JOIN "LSDash_materia" m ON q.materia_id = m.id
                    LEFT JOIN "LSDash_anoescolar" ae ON q.ano_escolar_id = ae.id
                    WHERE q.id = %s
                """, [questao_id])
                
                questao_data = cursor.fetchone()
                if not questao_data:
                    return None
                
                questao = {
                    'id': questao_data[0],
                    'titulo': questao_data[1],
                    'tipo': questao_data[2],
                    'materia': questao_data[3],
                    'ano_escolar': questao_data[4],
                    'imagens': [],
                    'alternativas': [],
                    'frases_vf': []
                }
                
                cursor.execute("""
                    SELECT imagem, legenda
                    FROM "LSDash_imagemquestao"
                    WHERE questao_id = %s
                """, [questao_id])
                
                for img_row in cursor.fetchall():
                    questao['imagens'].append({
                        'imagem': img_row[0],
                        'legenda': img_row[1]
                    })
                
                if questao['tipo'] == 'multipla':
                    cursor.execute("""
                        SELECT texto, correta, ordem
                        FROM "LSDash_alternativamultiplaescolha"
                        WHERE questao_id = %s
                        ORDER BY ordem
                    """, [questao_id])
                    
                    for alt_row in cursor.fetchall():
                        questao['alternativas'].append({
                            'texto': alt_row[0],
                            'correta': alt_row[1],
                            'ordem': alt_row[2]
                        })
                
                elif questao['tipo'] == 'vf':
                    cursor.execute("""
                        SELECT texto, verdadeira, ordem
                        FROM "LSDash_fraseverdadeirofalso"
                        WHERE questao_id = %s
                        ORDER BY ordem
                    """, [questao_id])
                    
                    for frase_row in cursor.fetchall():
                        questao['frases_vf'].append({
                            'texto': frase_row[0],
                            'verdadeira': frase_row[1],
                            'ordem': frase_row[2]
                        })
                
                return questao