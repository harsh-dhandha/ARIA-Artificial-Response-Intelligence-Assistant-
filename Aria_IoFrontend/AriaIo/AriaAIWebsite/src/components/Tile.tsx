import { ReactNode } from "react";
import { twMerge } from "tailwind-merge";

const titleHeight = 32;

type TileProps = {
  title?: string;
  children?: ReactNode;
  className?: string;
  childrenClassName?: string;
  padding?: boolean;
  backgroundColor?: string;
};

export const Tile: React.FC<TileProps> = ({
  children,
  title,
  className,
  childrenClassName,
  padding = true,
  backgroundColor = "transparent",
}) => {
  const contentPadding = padding ? 4 : 0;
  
  // Use a properly constructed backgroundColor class
  const bgClass = backgroundColor !== "transparent" ? `bg-${backgroundColor}` : "bg-transparent";
  
  return (
    <div
      className={twMerge(`flex flex-col text-foreground ${bgClass}`, className)}
    >
      {title && (
        <div className="text-xs font-mono font-semibold tracking-wider uppercase px-4 py-2">
          {title}
        </div>
      )}
      <div
        className={twMerge(`flex flex-col items-center grow w-full`, childrenClassName)}
        style={{
          height: `calc(100% - ${title ? titleHeight + "px" : "0px"})`,
          padding: `${contentPadding * 4}px`,
        }}
      >
        {children}
      </div>
    </div>
  );
};
