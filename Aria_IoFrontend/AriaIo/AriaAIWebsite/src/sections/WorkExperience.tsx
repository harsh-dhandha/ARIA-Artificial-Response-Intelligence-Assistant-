import hexawareLogo from "@/assets/images/Hexaware_logo (2).png";
import freshworkslogo from "@/assets/images/Freshworks.png";
import searchbloxlogo from "@/assets/images/searchblox.png";
import { SectionHeader } from "@/components/SectionHeader";
import Image from "next/image";
import { Card } from "@/components/Card";
import { Fragment } from "react";

const workExperience = [
  {
    name: "Harsh Dhandha",
    company: "Ziguratss Artwork LLP",
    position: "AI Intern",
    duration: "May 2024 – July 2024",
    description:
      "Developed frontend components for an attendance system, dashboard, and profile sections using React, Node.js, and Express.js. Implemented AI-based solutions for face recognition in attendance systems using computer vision techniques.",
    avatar: hexawareLogo,
    width: "2.5rem",
    height: "2.5rem",
  },
  {
    name: "Harsh Dhandha",
    company: "AWS Cloud Club, CHARUSAT",
    position: "Cloud Computing Intern",
    duration: "June 2024 – July 2024",
    description:
      "Deployed AWS cloud infrastructure (EC2, S3, Lambda) for departmental projects. Applied best practices for cloud security configurations and access management. Participated in hands-on workshops related to AWS cloud technologies.",
    avatar: freshworkslogo,
    width: "2.5rem",
    height: "2.5rem",
  },
  {
    name: "Vidhi",
    company: "Voldebug",
    position: "Web Developer",
    duration: "July 2024 – September 2024",
    description:
      "Developed and enhanced the frontend of the Voldebug website using React.js. Focused on UI/UX improvements, ensuring a more user-friendly and responsive design.",
    avatar: hexawareLogo,
    width: "2.5rem",
    height: "2.5rem",
},

{
    name: "Vidhi",
    company: "Nexeos",
    position: "Backend Developer",
    duration: "June 2024 - July 2024",
    description:
      "Built and optimized backend services using Node.js and Express.js. Integrated database management, authentication, and API development to improve system performance and security.",
    avatar: hexawareLogo,
    width: "2.5rem",
    height: "2.5rem",
},

];


export const WorkExperienceSection = () => {
  return (
    <section id="about">
      <div className="py-16 lg:py-24">
        <div className="container">
          <SectionHeader
            eyebrow="About Us"
            title="Technical Experience"
            description="Here’s a glimpse of our work experience and contributions."
          />
          <div className="mt-12 lg:mt-24 flex overflow-x-clip py-4 -my-4 [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)]">
            <div
              className="flex gap-8 pr-8 flex-none animate-move-left [animation-duration:30s] hover:[animation-play-state:paused]"
            >
              {[...new Array(2)].fill(0).map((_, index) => (
                <Fragment key={index}>
                  {workExperience.map((experience, i) => (
                    <Card
                      key={`${experience.name}-${experience.company}-${i}`}
                      className="p-6 max-w-xs md:p-8 md:max-w-md hover:-rotate-3 transition duration-300"
                    >
                      <div className="flex gap-4 items-center">
                        <div className="size-14 bg-gray-700 inline-flex items-center justify-center rounded-full flex-shrink-0">
                          <Image
                            src={experience.avatar}
                            alt={experience.name}
                            className="max-h-full"
                            style={{
                              width: `${experience.width}`,
                              height: `${experience.height}`,
                            }}
                          />
                        </div>
                        <div>
                          <div className="font-semibold">{experience.name}</div>
                          <div className="font-semibold">
                            {experience.position}
                          </div>
                          <div className="text-sm text-white/40">
                            {experience.company}
                          </div>
                          <div className="text-xs text-white/30">
                            {experience.duration}
                          </div>
                        </div>
                      </div>
                      <p className="mt-4 md:mt-6 text-sm md:text-base">
                        {experience.description}
                      </p>
                    </Card>
                  ))}
                </Fragment>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
