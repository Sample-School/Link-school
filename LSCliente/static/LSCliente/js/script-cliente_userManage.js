document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('userListModal');
    const abrirModalBtn = document.getElementById('abrir-modal');
    const fecharModalBtn = document.getElementById('fechar-modal');
    const buscarBtn = document.getElementById('btn-buscar-id');
    const inputId = document.getElementById('buscar-id');
    const usuarios = document.querySelectorAll('.usuario-item');
    const filtroInput = document.getElementById('filtro-modal');

    function preencherFormulario(usuario) {
        document.getElementById('usuario_id').value = usuario.id;
        document.querySelector('[name="nome"]').value = usuario.nome;
        document.querySelector('[name="email"]').value = usuario.email;
        document.querySelector('[name="password"]').value = '';
        const passConfirm = document.querySelector('[name="password_confirm"]');
        if (passConfirm) passConfirm.value = '';
    }

    abrirModalBtn.addEventListener('click', () => modal.classList.add('active'));
    fecharModalBtn.addEventListener('click', () => modal.classList.remove('active'));

    buscarBtn.addEventListener('click', function () {
        const id = inputId.value.trim();
        if (!id) return alert("Digite um ID válido");

        const user = [...usuarios].find(el => el.dataset.id === id);
        if (!user) return alert("Usuário não encontrado");

        preencherFormulario({
            id: user.dataset.id,
            nome: user.dataset.nome,
            email: user.dataset.email
        });
    });

    usuarios.forEach(el => {
        el.querySelector('.selecionar-usuario').addEventListener('click', () => {
            preencherFormulario({
                id: el.dataset.id,
                nome: el.dataset.nome,
                email: el.dataset.email
            });
            modal.classList.remove('active');
        });
    });

    filtroInput.addEventListener('input', function () {
        const termo = this.value.toLowerCase().trim();
        usuarios.forEach(el => {
            const nome = el.dataset.nome.toLowerCase();
            const email = el.dataset.email.toLowerCase();
            el.style.display = nome.includes(termo) || email.includes(termo) ? 'flex' : 'none';
        });
    });
});