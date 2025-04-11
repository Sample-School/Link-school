document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("userRegisterForm");
  const btnReset = document.getElementById("btnReset");
  const btnSave = document.getElementById("btnSave");

  btnReset.addEventListener("click", (event) => {
    event.preventDefault(); // Impede o envio do formulário, logo após reseta os campos.
    form.reset();
  });

  btnSave.addEventListener("click", () => {
    form.submit();
  });
});
