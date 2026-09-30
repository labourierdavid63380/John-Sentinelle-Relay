'use strict';
const el=id=>document.getElementById(id);
let ticket=new URLSearchParams(location.hash.slice(1)).get('pair');
history.replaceState(null,'',location.pathname); // Never keep a pairing secret in history.
let polling=false, online=false, listening=false;
async function api(path,body={}) {
 const response=await fetch('/api/phone/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),credentials:'same-origin',cache:'no-store'});
 let value;try{value=await response.json();}catch{throw Error('Réponse du service illisible.');}
 if(!response.ok)throw Error(value.error||'Service indisponible.');return value;
}
const labels={queued:'En attente du PC',running:'Traitement en cours, résultat non confirmé',completed:'Résultat reçu',expired:'Expirée',cancelled:'Annulée'};
async function status(){
 if(polling||document.hidden)return;polling=true;
 try {
  const data=await api('status');el('pairing').hidden=data.state!=='pending';
  if(data.state==='pending'){el('status').textContent='Confirmation attendue sur le PC';el('code').textContent=data.code;el('pc').textContent='PC · '+data.pc;}
  else {
   online=data.online;el('status').textContent='PC · '+data.pc+' — '+(online?'John est connecté':'John est hors ligne ou en pause');
   el('actions').hidden=false;el('send').disabled=!online;el('history').hidden=false;
   el('jobs').replaceChildren();
   for(const job of data.jobs){const a=document.createElement('article'),h=document.createElement('strong'),p=document.createElement('p');h.textContent=job.command+' · '+(labels[job.state]||job.state);p.textContent=job.result||'Aucune exécution terminée confirmée.';a.append(h,p);el('jobs').append(a);}
  }
 }catch(e){online=false;el('send').disabled=true;el('actions').hidden=true;el('pairing').hidden=true;el('status').textContent=e.message;}
 finally{polling=false;}
}
el('claim').onclick=async()=>{
 el('claim').disabled=true;
 try{const r=await api('claim',{ticket});ticket=null;el('claim').hidden=true;el('pairing').hidden=false;el('code').textContent=r.code;await status();}
 catch(e){el('status').textContent=e.message;el('claim').disabled=false;}
};
el('send').onclick=async()=>{
 const command=el('request').value.trim();
 if(!command){el('voice').textContent='Écrivez ou dictez d’abord une demande.';return;}
 el('send').disabled=true;
 try{await api('send',{command});el('request').value='';el('voice').textContent='Demande envoyée à John.';await status();}
 catch(e){el('status').textContent=e.message;el('send').disabled=!online;}
};
el('request').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();if(!el('send').disabled)el('send').click();}});
const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
if(SpeechRecognition){
 const recognition=new SpeechRecognition();recognition.lang='fr-FR';recognition.interimResults=false;recognition.continuous=false;
 recognition.onstart=()=>{listening=true;el('mic').textContent='⏹️ Écoute…';el('mic').setAttribute('aria-pressed','true');el('voice').textContent='John vous écoute…';};
 recognition.onresult=e=>{const said=e.results[e.results.length-1][0].transcript.trim();el('request').value=said;el('voice').textContent='Demande reconnue. Vérifiez-la puis appuyez sur Envoyer.';};
 recognition.onerror=e=>{el('voice').textContent=e.error==='not-allowed'?'Autorisez le microphone dans le navigateur.':'Reconnaissance vocale indisponible. Vous pouvez écrire la demande.';};
 recognition.onend=()=>{listening=false;el('mic').textContent='🎙️ Parler';el('mic').setAttribute('aria-pressed','false');};
 el('mic').onclick=()=>{if(listening)recognition.stop();else recognition.start();};
}else{el('mic').disabled=true;el('voice').textContent='Le vocal n’est pas pris en charge par ce navigateur. La saisie texte reste disponible.';}
if(ticket){el('status').textContent='Associer ce téléphone à John';el('claim').hidden=false;}
else status();
setInterval(()=>{if(!ticket)status();},4000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!ticket)status();});
