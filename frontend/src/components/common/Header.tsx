"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"

export default function Header(){

const pathname = usePathname()

const navItem = (href:string,label:string)=>{

const active = pathname === href

return(

<Link
href={href}
className={`px-4 py-2 rounded-lg text-sm font-medium transition
${active
? "bg-blue-600 text-white"
: "text-gray-600 hover:text-black"}
`}
>

{label}

</Link>

)

}

return(

<header className="h-[60px] border-b border-border bg-white flex items-center px-6">

<div className="flex items-center gap-8">

<div className="flex items-center gap-2 font-semibold text-lg">

<div className="w-8 h-8 bg-blue-600 rounded-md flex items-center justify-center text-white">
📊
</div>

<span>Analytica</span>

</div>

<nav className="flex gap-3">

{navItem("/ai-dashboard-builder","Dashboard Builder")}
{navItem("/executive-overview","Executive")}
{navItem("/sales-analytics-hub","Sales")}
{navItem("/operations-monitor","Operations")}

</nav>

</div>

</header>

)

}
