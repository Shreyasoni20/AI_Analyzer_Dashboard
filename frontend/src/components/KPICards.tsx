"use client"

export default function KPICards(){

return(

<div className="grid grid-cols-1 md:grid-cols-4 gap-6">

<div className="card p-6">

<p className="text-sm text-gray-500">
Total Revenue
</p>

<h2 className="text-2xl font-bold mt-2">
$48.7M
</h2>

<p className="text-green-500 text-sm mt-1">
+12.4%
</p>

</div>


<div className="card p-6">

<p className="text-sm text-gray-500">
Growth Rate
</p>

<h2 className="text-2xl font-bold mt-2">
12.4%
</h2>

<p className="text-green-500 text-sm mt-1">
+2.1%
</p>

</div>


<div className="card p-6">

<p className="text-sm text-gray-500">
Customer Acquisition
</p>

<h2 className="text-2xl font-bold mt-2">
3842
</h2>

<p className="text-red-500 text-sm mt-1">
-3.2%
</p>

</div>


<div className="card p-6">

<p className="text-sm text-gray-500">
Operational Efficiency
</p>

<h2 className="text-2xl font-bold mt-2">
87.3%
</h2>

<p className="text-green-500 text-sm mt-1">
+1.8%
</p>

</div>

</div>

)
}