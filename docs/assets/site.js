(function(){
var root=document.documentElement;
var saved=localStorage.getItem("kb-site-theme");if(saved){root.dataset.theme=saved;}
var theme=document.getElementById("site-theme");
function syncTheme(){if(theme){theme.textContent=root.dataset.theme==="dark"?"浅色":"深色";}}
if(theme){theme.addEventListener("click",function(){root.dataset.theme=root.dataset.theme==="dark"?"light":"dark";localStorage.setItem("kb-site-theme",root.dataset.theme);syncTheme();});}
syncTheme();
var lock=document.getElementById("site-lock");
if(lock){lock.addEventListener("click",function(){sessionStorage.removeItem("kb-unlock-key");location.reload();});}
var search=document.getElementById("section-search");
if(search){
var cards=Array.from(document.querySelectorAll(".kb-note-card"));
var buttons=Array.from(document.querySelectorAll(".category-button"));
var active="";
function apply(){var query=search.value.trim().toLocaleLowerCase("zh-CN");var visible=0;cards.forEach(function(card){var ok=(!query||(card.dataset.search||"").indexOf(query)>=0)&&(!active||card.dataset.category===active);card.hidden=!ok;if(ok)visible++;});document.getElementById("empty-state").style.display=visible?"none":"block";}
search.addEventListener("input",apply);
buttons.forEach(function(button){button.addEventListener("click",function(){var next=button.dataset.category;active=active===next?"":next;buttons.forEach(function(item){item.classList.toggle("active",item.dataset.category===active);});apply();});});
}
function bytesFromBase64(value){var raw=atob(value);var out=new Uint8Array(raw.length);for(var i=0;i<raw.length;i++)out[i]=raw.charCodeAt(i);return out;}
var protectedMedia=Array.from(document.querySelectorAll("[data-kb-src]"));
if(protectedMedia.length&&window.crypto&&crypto.subtle){
var storedKey=sessionStorage.getItem("kb-unlock-key");
if(storedKey){Promise.all(protectedMedia.map(async function(item){try{var response=await fetch(item.dataset.kbSrc,{cache:"no-store"});if(!response.ok)throw new Error("HTTP "+response.status);var bytes=new Uint8Array(await response.arrayBuffer());var key=await crypto.subtle.importKey("raw",bytesFromBase64(storedKey),"AES-GCM",false,["decrypt"]);var plain=await crypto.subtle.decrypt({name:"AES-GCM",iv:bytes.slice(0,12)},key,bytes.slice(12));var url=URL.createObjectURL(new Blob([plain],{type:item.dataset.kbType||"application/octet-stream"}));item.src=url;item.dataset.kbObjectUrl=url;}catch(error){console.warn("受保护图片解密失败",error);item.setAttribute("aria-label","受保护图片加载失败");}}));window.addEventListener("pagehide",function(){protectedMedia.forEach(function(item){if(item.dataset.kbObjectUrl)URL.revokeObjectURL(item.dataset.kbObjectUrl);});});}
}
})();