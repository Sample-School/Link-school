document.addEventListener("DOMContentLoaded", () => {
  const btnModal = document.getElementById("btnModal");
  const modalContent = document.getElementById("modalContent");
  const btnCloseModal = document.getElementById("btnCloseModal");
  const background = document.getElementById("background");
  const btnSave = document.getElementById("btnSave");
  const collabForm = document.getElementById("collabForm");

  btnModal.addEventListener("click", () => {
    modalContent.style.display = "flex";
    background.style.display = "block";
  });

  btnCloseModal.addEventListener("click", () => { 
    modalContent.style.display = "none";
    background.style.display = "none";
  });

  btnSave.addEventListener("click", (e) => {
    collabForm.submit();
  });
});