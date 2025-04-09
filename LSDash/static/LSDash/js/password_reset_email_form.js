const formSendEmail = document.getElementById("formSendEmail");

const btnSend = document.getElementById("btnSend");
btnSend.addEventListener("click", () => {
  // Envia o formulário para redifinir a senha.
  formSendEmail.submit();
});
