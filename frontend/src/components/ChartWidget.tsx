"use client"

import {
LineChart,
Line,
BarChart,
Bar,
PieChart,
Pie,
Cell,
XAxis,
YAxis,
Tooltip,
CartesianGrid
} from "recharts"

const COLORS = ["#2563EB","#7C3AED","#10B981","#F59E0B","#EF4444"]

export default function ChartWidget({chart}:any){

if(!chart) return null

const {type,data,title} = chart

return(

<div className="bg-white border rounded-xl p-6 shadow-sm">

<h2 className="text-lg font-semibold mb-4">
{title}
</h2>

<div style={{width:"100%",height:260}}>

{type==="line" && (

<LineChart width={400} height={260} data={data}>

<CartesianGrid strokeDasharray="3 3"/>

<XAxis dataKey="name"/>

<YAxis/>

<Tooltip/>

<Line
type="monotone"
dataKey="value"
stroke="#2563EB"
strokeWidth={3}
/>

</LineChart>

)}

{type==="bar" && (

<BarChart width={400} height={260} data={data}>

<CartesianGrid strokeDasharray="3 3"/>

<XAxis dataKey="name"/>

<YAxis/>

<Tooltip/>

<Bar dataKey="value" fill="#2563EB"/>

</BarChart>

)}

{type==="pie" && (

<PieChart width={400} height={260}>

<Pie data={data} dataKey="value" nameKey="name" outerRadius={90}>

{data.map((entry:any,index:number)=>(
<Cell key={index} fill={COLORS[index % COLORS.length]}/>
))}

</Pie>

<Tooltip/>

</PieChart>

)}

</div>

</div>

)

}