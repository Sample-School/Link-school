const formLogin = document.getElementById("formLogin");

const btnSend = document.getElementById("btnSend");
btnSend.addEventListener("click", () => {
  // Envia o formulário de login.
  formLogin.submit();
});
