import Timer from "@/components/ui/shared/Timer";
import Loader from "@/components/ui/shared/Loader";
import GoalsCard from "@/components/ui/shared/GoalsCard";
import { StudyHistChart } from "@/components/ui/shared/StudyHistChart";


const MyFocus = () => {
  return (
    <div className="grid grid-cols-8 gap-4 w-full">
      {/* Main section */}
      <div className="lg:col-span-5 full home-container col-span-8 ">
        {/* Header */}
        <div className="home-header">
          <h1 className="h2-bold md:h1-bold text-left w-full text-light-2">
            My Focus
          </h1>
          <p className="text-light-2"> Track your journey. </p>
          <p className="text-light-2"> See how far you’ve come — and push forward!</p>
        </div>
        {/* Study History*/}        
        <div className="home-posts">
          <h2 className="h3-bold md:h2-bold text-left w-full">        
            <StudyHistChart/>
          </h2>
        </div>
      </div>
      {/* Focus Widget */}
      <div className="lg:col-span-3 lg:grid col-span-0 right-side-container ">
        <div className="py-10 mt-4 gap-4">
          <Timer />
          <GoalsCard />          
        </div>
      </div >
    </div>
  )
}

export default MyFocus
