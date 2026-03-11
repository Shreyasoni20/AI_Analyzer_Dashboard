"use client"

import Header from "@/components/common/Header"
import { useEffect, useState } from "react"
import axios from "axios"

export default function Page(){

const [data,setData] = useState<any>(null)

useEffect(()=>{

axios.get("http://localhost:8000/sales-kpis")
.then(res=>setData(res.data))

},[])

if(!data) return null

const formatINR = (value:number)=>{
return "₹" + value.toLocaleString("en-IN")
}

return(

<div className="min-h-screen bg-background">

<Header/>

<div className="pt-[70px] px-6 space-y-6">

<h1 className="text-2xl font-bold">
Sales Analytics Hub
</h1>

{/* KPI Cards */}

<div className="grid grid-cols-6 gap-4">

<KPI
title="Total Revenue"
value={formatINR(data.total_revenue)}
/>

<KPI
title="Conversion Rate"
value={`${data.conversion_rate}%`}
/>

<KPI
title="Avg Deal Size"
value={formatINR(data.avg_deal_size)}
/>

<KPI
title="Pipeline Velocity"
value={formatINR(data.pipeline_velocity)}
/>

<KPI
title="Win Rate"
value={`${data.win_rate}%`}
/>

<KPI
title="Open Deals"
value={data.open_deals}
/>

</div>

{/* Pipeline */}

<div className="bg-card border border-border rounded-xl p-6">

<h2 className="text-lg font-semibold mb-4">
Sales Pipeline
</h2>

{[
{stage:"Prospecting",value:80},
{stage:"Qualification",value:65},
{stage:"Proposal",value:40},
{stage:"Negotiation",value:25},
{stage:"Closed Won",value:12},
{stage:"Closed Lost",value:8}
].map((s,i)=>(

<div key={i} className="mb-4">

<div className="flex justify-between mb-1">
<span>{s.stage}</span>
<span>{s.value}%</span>
</div>

<div className="w-full bg-gray-200 rounded h-3">

<div
className="bg-blue-600 h-3 rounded"
style={{width:`${s.value}%`}}
/>

</div>

</div>

))}

</div>

</div>

</div>

)

}

function KPI({title,value}:any){

return(

<div className="bg-card border border-border rounded-xl p-4">

<div className="text-sm text-muted-foreground">
{title}
</div>

<div className="text-xl font-bold">
{value}
</div>

</div>

)

}
