const key = "accessible-font";
const toggle = document.querySelector("#accessible-font");
const root = document.documentElement;

if (sessionStorage.getItem(key) === "on") {
    root.classList.add("accessible-font");
    toggle.checked = true;
}

toggle.addEventListener("change", () => {
    root.classList.toggle("accessible-font", toggle.checked);
    sessionStorage.setItem(key, toggle.checked ? "on" : "off");
});