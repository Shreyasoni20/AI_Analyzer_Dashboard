'use client'

export default function ChatArea({messages,onSend,inputValue,setInputValue}:any){

return(

<div className="flex flex-col flex-1">

<div className="flex-1 overflow-auto p-6 space-y-4">

{messages.map((m:any)=>(

<div key={m.id} className={m.role==="ai"?"text-blue-300":"text-white"}>

{m.content}

</div>

))}

</div>

<div className="p-4 border-t border-border">

<input
value={inputValue}
onChange={(e)=>setInputValue(e.target.value)}
placeholder="Describe dashboard..."
className="w-full bg-card p-3 rounded"
/>

<button
onClick={()=>onSend()}
className="mt-3 bg-primary px-4 py-2 rounded"
>
Generate Dashboard
</button>

</div>

</div>

)

}