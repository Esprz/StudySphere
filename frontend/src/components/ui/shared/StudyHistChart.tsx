"use client"

import { TrendingUp } from "lucide-react"
import { Area, AreaChart, CartesianGrid, XAxis } from "recharts"

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
const chartData = [
  { month: "January", focus: 186 },
  { month: "February", focus: 305 },
  { month: "March", focus: 237 },
  { month: "April", focus: 73 },
  { month: "May", focus: 209 },
  { month: "June", focus: 214 },
]

const chartConfig = {
  focus: {
    //label: "Focus minutes",
    color: "hsl(var(--chart-1))",
  },
} satisfies ChartConfig

export const StudyHistChart = () => {
  return (
    <Card>
      
      <CardHeader>
        {/*<CardTitle>Area Chart</CardTitle>
        <CardDescription>
          Showing total visitors for the last 6 months
        </CardDescription>*/}
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig}>
          <AreaChart
            accessibilityLayer
            data={chartData}
            margin={{
              left: 12,
              right: 12,
            }}
          >
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="month"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tickFormatter={(value) => value.slice(0, 3)}
            />
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent indicator="line" />}
            />
            <Area
              dataKey="focus"
              type="natural"
              fill="var(--color-focus)"
              fillOpacity={0.4}
              stroke="var(--color-focus)"
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
      {/* 
      <CardFooter>
        <div className="flex w-full items-start gap-2 text-sm">
          <div className="grid gap-2">
            <div className="flex items-center gap-2 font-medium leading-none">
              Trending up by 5.2% this month <TrendingUp className="h-4 w-4" />
            </div>
            <div className="flex items-center gap-2 leading-none text-muted-foreground">
              January - June 2024
            </div>
          </div>
        </div>
      </CardFooter>*/}
    </Card>
  )
}
