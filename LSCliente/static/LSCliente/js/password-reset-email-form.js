const form = document.querySelector(".container__form");
const btnSend = document.querySelector(".btn-send");

btnSend.addEventListener("click", () => {
  form.submit();
});
