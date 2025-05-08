const form = document.querySelector(".container__form");
const button = document.querySelector(".btn-send");

button.addEventListener("click", () => {
  form.submit();
});
