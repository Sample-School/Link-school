document.addEventListener('DOMContentLoaded', function() {
    // Preview da imagem quando selecionada
    const inputFoto = document.querySelector('input[type="file"]');
    if (inputFoto) {
        inputFoto.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                
                // Verificar se já existe uma preview
                let previewContainer = document.querySelector('.foto-preview');
                if (!previewContainer) {
                    previewContainer = document.createElement('div');
                    previewContainer.className = 'foto-preview';
                    this.parentNode.appendChild(previewContainer);
                }
                
                // Limpar conteúdo anterior
                previewContainer.innerHTML = '';
                
                reader.onload = function(e) {
                    const img = document.createElement('img');
                    img.src = e.target.result;
                    img.alt = 'Foto do usuário';
                    img.className = 'user-photo-preview';
                    previewContainer.appendChild(img);
                }
                
                reader.readAsDataURL(file);
            }
        });
    }
    
    // Avisar se o usuário tentar sair sem salvar alterações
    const form = document.getElementById('usuario-form');
    if (form) {
        let formChanged = false;
        
        form.addEventListener('change', function() {
            formChanged = true;
        });
        
        // Quando o usuário sair da página
        window.addEventListener('beforeunload', function(e) {
            if (formChanged) {
                e.preventDefault();
                e.returnValue = 'Você tem alterações não salvas. Deseja realmente sair?';
                return e.returnValue;
            }
        });
        
        // Quando o formulário for enviado, não precisamos mais do alerta
        form.addEventListener('submit', function() {
            formChanged = false;
        });
    }
});