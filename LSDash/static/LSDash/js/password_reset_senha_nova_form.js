const form = document.getElementById("form");

const btnSend = document.getElementById("btnSend");
btnSend.addEventListener("click", () => {
  // Envia o formulário para redifinir a senha.
  form.submit();
});
