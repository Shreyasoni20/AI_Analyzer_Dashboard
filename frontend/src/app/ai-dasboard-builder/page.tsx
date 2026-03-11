"use client"

import Header from "@/components/common/Header"
import ChartWidget from "@/components/ChartWidget"
import axios from "axios"
import { useState } from "react"

export default function Page(){

const [messages,setMessages] = useState<any[]>([
{
role:"assistant",
text:"Hello! I'm your AI Dashboard Builder. Describe the dashboard you need in plain English."
}
])

const [input,setInput] = useState("")
const [charts,setCharts] = useState<any[]>([])

const suggestions = [
"Show me Q1 sales performance by region",
"Create a product revenue comparison chart",
"Build an executive KPI summary dashboard",
"Analyze customer acquisition trends"
]

function applySuggestion(text:string){
setInput(text)
}

async function sendMessage(){

if(!input) return

const userMsg = {role:"user",text:input}
setMessages((prev)=>[...prev,userMsg])

try{

const res = await axios.post(
"http://localhost:8000/generate",
{prompt:input}
)

setMessages((prev)=>[
...prev,
{
role:"assistant",
text:res.data.insight
}
])

setCharts(res.data.charts)

}catch{

setMessages((prev)=>[
...prev,
{role:"assistant",text:"Error generating dashboard"}
])

}

setInput("")
}

return(

<div className="min-h-screen bg-background">

<Header/>

<div className="flex pt-[70px] h-[calc(100vh-70px)]">

{/* LEFT CHAT */}

<div className="w-2/3 border-r border-border flex flex-col">

<div className="p-6 space-y-6 flex-1 overflow-y-auto">

<h2 className="text-lg font-semibold">
AI Dashboard Builder
</h2>

<p className="text-sm text-muted-foreground">
Powered by Analytica AI
</p>

{messages.map((m,i)=>(
<div
key={i}
className={`max-w-[600px] p-4 rounded-xl
${m.role==="assistant"
?"bg-muted"
:"bg-blue-600 text-white ml-auto"}
`}
>
{m.text}
</div>
))}

{/* Suggestions */}

<div className="flex flex-wrap gap-3">

{suggestions.map((s,i)=>(
<button
key={i}
onClick={()=>applySuggestion(s)}
className="px-4 py-2 border rounded-full text-sm hover:bg-muted"
>
{s}
</button>
))}

</div>

</div>

{/* INPUT */}

<div className="border-t border-border p-4">

<div className="flex gap-2">

<input
value={input}
onChange={(e)=>setInput(e.target.value)}
placeholder="Describe the dashboard..."
className="flex-1 border border-border rounded-lg px-4 py-2"
/>

<button
onClick={sendMessage}
className="bg-blue-600 text-white px-5 py-2 rounded-lg"
>
Generate
</button>

</div>

</div>

</div>

{/* RIGHT PREVIEW */}

<div className="w-1/3 p-6 overflow-y-auto">

<h3 className="font-semibold mb-4">
Live Preview
</h3>

{charts.length === 0 ? (

<div className="border border-border rounded-xl p-10 text-center">

<div className="text-4xl mb-2">📊</div>

<p className="font-medium">No Dashboard Yet</p>

<p className="text-sm text-muted-foreground">
Describe what you want to visualize in the chat
</p>

</div>

):( 

<div className="space-y-6">

{charts.map((chart:any)=>(
<ChartWidget key={chart.id} chart={chart}/>
))}

</div>

)}

</div>

</div>

</div>

)

}
