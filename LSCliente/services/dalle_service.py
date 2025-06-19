# Serviço para geração de imagens educativas usando DALL-E 3
import openai
import requests
import os
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)


class DalleImageService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def gerar_prompt_educacional(self, questao_data: Dict[str, Any]) -> str:
        """Cria prompts específicos baseados na matéria e contexto da questão"""
        materia = questao_data.get('materia', '').lower()
        titulo = questao_data.get('titulo', '')
        nivel_escolar = questao_data.get('ano_escolar', '9º Ano')
        
        # Cada matéria tem seu contexto visual específico
        contextos_materia = {
            'matemática': 'ilustração educativa de matemática, gráficos, equações visuais, geometria',
            'física': 'diagrama científico de física, experimentos, forças, movimento, energia',
            'química': 'ilustração de química, moléculas, reações químicas, laboratório',
            'biologia': 'ilustração biológica, células, organismos, natureza, anatomia',
            'história': 'ilustração histórica, época histórica, civilizações, monumentos',
            'geografia': 'mapa, paisagem geográfica, relevo, clima, regiões',
            'português': 'ilustração literária, livros, texto, linguagem, comunicação',
            'sociologia': 'sociedade, grupos sociais, interação humana, comunidade'
        }
        
        contexto_visual = contextos_materia.get(materia, 'ilustração educativa')
        
        # Montar o prompt final
        prompt = f"""
        Crie uma ilustração educativa para {nivel_escolar} sobre {materia}.
        Contexto: {titulo[:100]}...
        
        Estilo: {contexto_visual}, didático, colorido, apropriado para estudantes.
        Qualidade: alta resolução, limpo, profissional, educativo.
        
        Evite: texto, números, letras, símbolos complexos.
        Foque em: representação visual clara e educativa do conceito.
        """
        
        return prompt.strip()
    
    def gerar_imagem_questao(self, questao_data: Dict[str, Any], 
                           tamanho: str = "1024x1024") -> Optional[str]:
        """
        Gera uma imagem educativa para questão usando DALL-E 3
        
        Args:
            questao_data: Dados da questão (matéria, título, etc.)
            tamanho: Dimensões da imagem (1024x1024, 1024x1792, 1792x1024)
            
        Returns:
            Caminho da imagem salva ou None se deu erro
        """
        try:
            # Criar prompt específico para a questão
            prompt = self.gerar_prompt_educacional(questao_data)
            
            logger.info(f"Gerando imagem para questão {questao_data.get('id')} com prompt: {prompt[:100]}...")
            
            # Chamar DALL-E 3 para gerar a imagem
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=tamanho,
                quality="standard",  # "hd" para maior qualidade mas mais caro
                n=1
            )
            
            # Pegar URL da imagem gerada
            image_url = response.data[0].url
            
            # Baixar e salvar no storage do Django
            saved_path = self._baixar_e_salvar_imagem(
                image_url, 
                questao_data.get('id', 'unknown')
            )
            
            return saved_path
            
        except Exception as e:
            logger.error(f"Erro ao gerar imagem: {str(e)}")
            return None
    
    def _baixar_e_salvar_imagem(self, image_url: str, questao_id: str) -> Optional[str]:
        """Faz download da imagem gerada e salva no sistema de arquivos"""
        try:
            # Download da imagem
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Criar nome único para evitar conflitos
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            hash_id = hashlib.md5(f"{questao_id}_{timestamp}".encode()).hexdigest()[:8]
            filename = f"questoes/dalle/{questao_id}_{hash_id}.png"
            
            # Salvar usando o storage do Django
            file_content = ContentFile(response.content)
            saved_path = default_storage.save(filename, file_content)
            
            logger.info(f"Imagem salva em: {saved_path}")
            return saved_path
            
        except Exception as e:
            logger.error(f"Erro ao baixar/salvar imagem: {str(e)}")
            return None
    
    def gerar_imagem_com_cache(self, questao_data: Dict[str, Any]) -> Optional[str]:
        """Evita regenerar imagens iguais usando cache baseado no conteúdo"""
        # Hash do conteúdo para identificar questões similares
        content_hash = hashlib.md5(
            f"{questao_data.get('titulo', '')}{questao_data.get('materia', '')}".encode()
        ).hexdigest()
        
        cache_filename = f"questoes/dalle/cache_{content_hash}.png"
        
        # Se já existe, usar a versão em cache
        if default_storage.exists(cache_filename):
            logger.info(f"Usando imagem do cache: {cache_filename}")
            return cache_filename
        
        # Senão, gerar nova imagem
        return self.gerar_imagem_questao(questao_data)
    
    def gerar_multiplas_imagens(self, questoes_data: list, 
                              progresso_callback=None) -> Dict[str, str]:
        """
        Processa várias questões de uma vez com acompanhamento do progresso
        """
        resultados = {}
        total = len(questoes_data)
        
        for i, questao in enumerate(questoes_data, 1):
            questao_id = str(questao.get('id', f'questao_{i}'))
            
            try:
                imagem_path = self.gerar_imagem_questao(questao)
                if imagem_path:
                    resultados[questao_id] = imagem_path
                    logger.info(f"Imagem gerada para questão {questao_id}")
                else:
                    logger.warning(f"Falha ao gerar imagem para questão {questao_id}")
                
                # Atualizar progresso se tiver callback
                if progresso_callback:
                    progresso_callback(i, total, questao_id)
                    
            except Exception as e:
                logger.error(f"Erro ao processar questão {questao_id}: {str(e)}")
                continue
        
        return resultados


# Instância única do serviço para usar em todo o projeto
dalle_service = DalleImageService()