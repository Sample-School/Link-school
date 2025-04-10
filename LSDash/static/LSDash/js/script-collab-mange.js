$(document).ready(function() {
    // Quando clicar no botão de selecionar
    $('.select-user-btn').click(function() {
        // Pega o user_id da linha (tr) pai do botão
        var userId = $(this).closest('tr').data('user-id');
        
        // Atualiza o campo de input com o ID do usuário
        $('#user_id').val(userId);
        
        // Envia o formulário de pesquisa
        $('#userSearchForm').submit();
        
        // Fecha o modal
        $('#userModal').modal('hide');
    });
});