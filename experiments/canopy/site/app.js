"use strict";
// C1 is an offline *fictional* exhibit. No radios, camera, filesystem writes,
// remote resources, persistent identities, or model execution are invoked.
const nodes = Object.freeze({
  scout: {
    id: "PHIPIE-DEMO-001", name: "Scout Pie", role: "TRAIL GUIDE",
    greeting: "PhiOS loves you, bro.",
    title: "The mossy crossroads",
    story: "A small brass sign points in three directions: CURIOSITY, KINDNESS, and SNACKS. The trail guide has no idea which one leads to enlightenment, but it strongly recommends packing water.",
    neighbors: [["Professor Phi", "Fictional library · 0 measured hops"], ["Queso Relay", "Fictional bark station · 0 measured hops"], ["Dream Pie", "Fictional story node · 0 measured hops"]]
  },
  professor: {
    id: "PHIPIE-DEMO-002", name: "Professor Phi", role: "KNOWLEDGE KEEPER",
    greeting: "Your questions are welcome here.",
    title: "The library of tiny wonders",
    story: "Today's lesson: a forest is a neighborhood of overlapping relationships. This page is only a storybook. Any future scientific field notes must have real sources and dates.",
    neighbors: [["Scout Pie", "Fictional trail guide · 0 measured hops"], ["Dream Pie", "Fictional imagination station · 0 measured hops"]]
  },
  queso: {
    id: "PHIPIE-DEMO-003", name: "Queso Relay", role: "CHIEF OF GOOD DOGS",
    greeting: "Bark twice for distributed systems.",
    title: "A very important dispatch",
    story: "The message arrives in full: WOOF. Our analysts conclude that snacks are desirable and that nobody should mistake this pretend relay for a verified emergency network.",
    neighbors: [["Scout Pie", "Fictional trail guide · 0 measured hops"], ["Professor Phi", "Fictional library · 0 measured hops"]]
  },
  dreamer: {
    id: "PHIPIE-DEMO-004", name: "Dream Pie", role: "STORY WEAVER",
    greeting: "Every strange idea starts somewhere.",
    title: "The tree that traded postcards",
    story: "At sunset, four little lunchboxes agreed to trade stories instead of secrets. No names. No profiles. Just adventures someone might carry home in a pocket.",
    neighbors: [["Queso Relay", "Fictional bark station · 0 measured hops"], ["Professor Phi", "Fictional library · 0 measured hops"]]
  }
});
const byId = (id) => document.getElementById(id);
let selected = nodes.scout;
function render() {
  selected = nodes[byId("nodeSelect").value] || nodes.scout;
  byId("nodeName").textContent = selected.name;
  byId("nodeRole").textContent = selected.role;
  byId("nodeGreeting").textContent = selected.greeting;
  byId("nodeId").textContent = selected.id;
  const list = byId("neighborList");
  list.replaceChildren();
  for (const [name, detail] of selected.neighbors) {
    const item = document.createElement("li");
    item.textContent = name;
    const description = document.createElement("span");
    description.textContent = detail;
    item.append(description);
    list.append(item);
  }
  byId("storyPanel").hidden = true;
}
byId("nodeSelect").addEventListener("change", render);
byId("storyBtn").addEventListener("click", () => {
  byId("storyTitle").textContent = selected.title;
  byId("storyText").textContent = selected.story;
  byId("storyPanel").hidden = false;
  byId("storyPanel").scrollIntoView({block:"nearest", behavior:"auto"});
});
byId("postcardBtn").addEventListener("click", () => {
  const text = [
    "PHIPIE CANOPY — FICTIONAL OFFLINE POSTCARD", selected.name, selected.id,
    selected.greeting, "", selected.title, selected.story, "",
    "SIMULATED C1 ARTIFACT. Not a LightBridge transfer or node verification.",
    "No identity or location information collected."
  ].join("\n");
  const file = new Blob([text], {type: "text/plain;charset=utf-8"});
  const url = URL.createObjectURL(file);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = selected.id.toLowerCase() + "-postcard.txt";
  document.body.append(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
byId("noteForm").addEventListener("submit", (event) => {
  event.preventDefault();
  const field = byId("noteInput");
  const value = field.value.trim().slice(0, 120);
  if (!value) return;
  const item = document.createElement("li");
  item.textContent = value; // never HTML-interpolate user notes
  const list = byId("noteList");
  list.prepend(item);
  while (list.childElementCount > 4) list.lastElementChild.remove();
  field.value = "";
});
render();
