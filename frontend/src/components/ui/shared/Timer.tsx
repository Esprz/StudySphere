import React, { useState, useEffect } from 'react';

const Timer = () => {
  const [time, setTime] = useState(0); 
  const [isRunning, setIsRunning] = useState(false);


  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    if (isRunning) {
      timer = setInterval(() => {
        setTime((prevTime) => prevTime + 1);
      }, 1000);
    } else if (!isRunning && timer) {
      clearInterval(timer);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isRunning]);


  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60).toString().padStart(2, '0');
    const seconds = (time % 60).toString().padStart(2, '0');
    return `${minutes}:${seconds}`;
  };


  const handleStartPause = () => {
    setIsRunning((prev) => !prev);
  };

  const handleStop = () => {
    setIsRunning(false);
    setTime(0);
  };

  return (
    <section className="flex flex-col items-center justify-center">
      {/* clock */}
      <div className="relative flex items-center justify-center w-60 h-60 rounded-full border-4 border-primary-500 bg-white shadow-md">
        <span className="text-4xl font-bold text-primary-500">{formatTime(time)}</span>
      </div>

      {/* button */}
      <div className="flex gap-8 mt-8">
        <button
          onClick={handleStartPause}
          className="px-4 py-2 text-white bg-primary-500 rounded-lg shadow-md hover:bg-primary-600 text-lg"
        >
          {isRunning ? 'Pause' : 'Start'}
        </button>
        <button
          onClick={handleStop}
          className="px-4 py-2 text-white bg-secondary-500 rounded-lg shadow-md hover:bg-secondary-600 text-lg"
        >
          Stop
        </button>
      </div>
    </section>
  );
};

export default Timer;