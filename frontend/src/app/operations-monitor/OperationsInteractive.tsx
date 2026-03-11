"use client"

import Header from "@/components/common/Header"
import {
ResponsiveContainer,
LineChart,
Line,
XAxis,
YAxis,
Tooltip
} from "recharts"

const perf = [
{time:"09:00",cpu:40,network:20},
{time:"09:10",cpu:50,network:30},
{time:"09:20",cpu:60,network:25},
{time:"09:30",cpu:55,network:18},
{time:"09:40",cpu:48,network:10},
{time:"09:50",cpu:42,network:15},
{time:"10:00",cpu:35,network:28}
]

const incidents = [
{
title:"Database Connection Pool Exhausted",
type:"Critical"
},
{
title:"High CPU Usage on API Server",
type:"Warning"
},
{
title:"Elevated Error Rate",
type:"Warning"
}
]

export default function Page(){

return(

<div className="min-h-screen bg-background">

<Header/>

<div className="pt-[70px] px-6 space-y-6">

<h1 className="text-2xl font-bold">
Operations Monitor
</h1>

{/* SYSTEM KPIs */}

<div className="grid grid-cols-4 gap-4">

<KPI title="System Health Score" value="78/100"/>
<KPI title="Active Incidents" value="3"/>
<KPI title="Avg Response Time" value="190ms"/>
<KPI title="Overall Uptime" value="98.97%"/>

</div>

{/* PERFORMANCE CHART */}

<div className="bg-card border border-border rounded-xl p-6">

<h2 className="font-semibold mb-4">
Performance Metrics
</h2>

<ResponsiveContainer width="100%" height={300}>

<LineChart data={perf}>

<XAxis dataKey="time"/>

<YAxis/>

<Tooltip/>

<Line
type="monotone"
dataKey="cpu"
stroke="#ef4444"
/>

<Line
type="monotone"
dataKey="network"
stroke="#2563eb"
/>

</LineChart>

</ResponsiveContainer>

</div>

{/* INCIDENT LIST */}

<div className="bg-card border border-border rounded-xl p-6">

<h2 className="font-semibold mb-4">
Incident Feed
</h2>

<div className="space-y-3">

{incidents.map((i,index)=>(
<div
key={index}
className="border rounded-lg p-3 bg-muted"
>

<div className="font-semibold">
{i.title}
</div>

<div className="text-sm text-muted-foreground">
{i.type}
</div>

</div>
))}

</div>

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