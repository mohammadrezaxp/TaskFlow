(() => {
  const button=document.getElementById('theme-toggle');
  const saved=localStorage.getItem('taskflow-theme');
  if(saved==='dark') document.body.classList.add('dark');
  button?.addEventListener('click',()=>{document.body.classList.toggle('dark');localStorage.setItem('taskflow-theme',document.body.classList.contains('dark')?'dark':'light')});
  const token=document.querySelector('[name=csrfmiddlewaretoken]')?.value;
  let dragging=null;
  document.querySelectorAll('[data-task]').forEach(card=>{
    card.addEventListener('dragstart',event=>{dragging=card;event.dataTransfer.setData('text/plain',card.dataset.task)});
    card.addEventListener('dragend',()=>{dragging=null});
  });
  document.querySelectorAll('[data-lane]').forEach(lane=>{
    lane.addEventListener('dragover',event=>event.preventDefault());
    lane.addEventListener('drop',async event=>{
      event.preventDefault();if(!dragging)return;
      const card=dragging;const status=lane.dataset.lane;
      try{
        const response=await fetch('/api/v1/tasks/'+card.dataset.task+'/reorder/',{
          method:'PATCH',headers:{'Content-Type':'application/json','X-CSRFToken':token},
          body:JSON.stringify({status,position:lane.querySelectorAll('[data-task]').length})});
        if(!response.ok)throw Error('Move failed. Refresh and try again.');
        lane.append(card);const label=card.querySelector('[data-status]');if(label)label.textContent=status.replaceAll('_',' ');
        document.querySelectorAll('[data-lane]').forEach(column=>{const count=column.querySelector('[data-count]');if(count)count.textContent=column.querySelectorAll('[data-task]').length});
      }catch(error){const toast=document.getElementById('toast');toast.textContent=error.message;toast.classList.add('show');setTimeout(()=>toast.classList.remove('show'),4000)}
    });
  });
  document.querySelectorAll('form[data-confirm]').forEach(form=>form.addEventListener('submit',event=>{if(!confirm(form.dataset.confirm))event.preventDefault()}));
})();
