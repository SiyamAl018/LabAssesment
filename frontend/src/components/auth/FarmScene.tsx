import { Homestead } from '../ui/VillageArt';
import { useEffect, useId, useRef, useState } from 'react';

/** Decorative vector scene: no images, external assets, animation libraries or timers. */
export default function FarmScene({ paused }: { paused: boolean }) {
  const id = useId().replace(/:/g, '');
  const container = useRef<HTMLDivElement>(null);
  const inView = useRef(true);
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    const onVisibility = () => setVisible(inView.current && !document.hidden);
    const observer = new IntersectionObserver(([entry]) => { inView.current = entry.isIntersecting; onVisibility(); });
    if (container.current) observer.observe(container.current);
    document.addEventListener('visibilitychange', onVisibility);
    return () => { observer.disconnect(); document.removeEventListener('visibilitychange', onVisibility); };
  }, []);
  const ref = (name: string) => `url(#${id}-${name})`;
  return <div ref={container} className={`farm-scene ${paused || !visible ? 'farm-paused' : ''}`} aria-hidden="true">
    <svg viewBox="0 0 800 660" preserveAspectRatio="xMidYMax meet" focusable="false">
      <defs>
        <linearGradient id={`${id}-sky`} x2="0" y2="1"><stop stopColor="#abcbb5"/><stop offset=".65" stopColor="#f0e6b7"/><stop offset="1" stopColor="#c9d29b"/></linearGradient>
        <linearGradient id={`${id}-water`} x2=".7" y2="1"><stop stopColor="#a2c4ad"/><stop offset="1" stopColor="#367d70"/></linearGradient>
        <linearGradient id={`${id}-grass`} x2=".2" y2="1"><stop stopColor="#88a862"/><stop offset="1" stopColor="#345f3f"/></linearGradient>
        <radialGradient id={`${id}-light`}><stop stopColor="#fff3c8" stopOpacity=".8"/><stop offset="1" stopColor="#fff3c8" stopOpacity="0"/></radialGradient>
        <linearGradient id={`${id}-cow`} x2=".7" y2="1"><stop stopColor="#f0d8ab"/><stop offset=".5" stopColor="#bd8956"/><stop offset="1" stopColor="#825536"/></linearGradient>
        <g id={`${id}-rice`} strokeLinecap="round"><path d="M0 0Q-4-24 0-46M0-9Q-15-19-13-31M0-17Q12-27 14-38M0-27Q-8-37-7-46" stroke="#487544" strokeWidth="2"/><path d="M0-43Q5-52 9-48" stroke="#d9cf7c" strokeWidth="3"/></g>
        <g id={`${id}-chick`}><ellipse cy="12" rx="12" ry="3" fill="#284e36" opacity=".2"/><path d="M-3 7L-4 13M4 7L5 13" stroke="#bb8043" strokeWidth="1.5"/><ellipse rx="10" ry="8" fill="#f4d891"/><circle cx="7" cy="-6" r="6" fill="#f8e3a4"/><path d="M12-7L17-4L12-3" fill="#b87e39"/><circle cx="9" cy="-7" r="1" fill="#283b31"/></g>
      </defs>
      <path fill={ref('sky')} d="M0 0H800V660H0Z"/>
      <circle cx="625" cy="175" r="155" fill={ref('light')}/><circle cx="625" cy="175" r="38" fill="#fff0bd" opacity=".85"/>
      <g fill="#fff9e4" opacity=".5"><g className="farm-cloud"><path d="M30 180Q26 160 48 158Q54 132 79 146Q99 130 110 155Q135 151 141 174Z"/></g><g className="farm-cloud farm-cloud-two"><path d="M430 92Q430 74 450 75Q467 43 491 71Q518 60 528 88Z"/></g></g>
      <g className="farm-birds" stroke="#547667" strokeWidth="2" fill="none"><path d="M380 180q8-9 16 0q8-9 16 0M427 162q6-7 12 0q6-7 12 0M346 164q5-6 10 0q5-6 10 0"/></g>
      <path d="M0 294Q180 273 330 284Q560 255 800 284V660H0Z" fill="#7d9b72"/>
      <path d="M0 345Q250 292 470 327Q650 296 800 322V660H0Z" fill="#a6b57a"/>
      <path d="M0 423Q250 290 800 390V660H0Z" fill="#77985c"/>
      <g fill="none" stroke="#c6cd8c" strokeWidth="8" opacity=".6"><path d="M-50 450Q240 305 820 420M-40 478Q260 328 830 448M-30 508Q270 350 840 478"/></g>
      <g transform="translate(244 230) scale(1.55)"><Homestead/></g>
      <g stroke="#6b7550" strokeWidth="4"><path d="M8 390L240 369M8 407L240 386M35 375V427M90 373V416M145 369V405M201 365V398"/></g>
      <path d="M0 497Q220 385 411 466Q590 387 800 449V660H0Z" fill={ref('grass')}/>
      <path d="M431 504Q503 447 646 462Q755 468 765 528Q746 600 593 594Q460 595 427 548Q410 525 431 504Z" fill="#b1b27b"/>
      <path d="M443 508Q505 460 644 475Q742 479 751 528Q727 582 592 580Q470 581 440 543Q426 526 443 508Z" fill={ref('water')}/>
      <g stroke="#e0e7c4" fill="none" opacity=".5"><ellipse className="farm-ripple" cx="579" cy="524" rx="35" ry="6"/><ellipse className="farm-ripple farm-ripple-two" cx="681" cy="548" rx="24" ry="4"/><path d="M468 527h40M622 492h57M521 557h39"/></g>
      <g className="farm-fish" transform="translate(590 522)"><path d="M-12 0Q0-16 15-2L23-9L21 3L14 2Q0-6-12 0" fill="#e2b76b"/><path d="M-14 7Q5 13 23 6" stroke="#dce8c4" fill="none"/></g>
      <g transform="translate(64 365)"><path d="M0 120Q12 55 5-20M9 70L42 16M6 45L-26 3" stroke="#6c7250" strokeWidth="14" fill="none"/><g className="farm-leaves" fill="#386d4a"><ellipse cx="-19" cy="-10" rx="53" ry="42"/><ellipse cx="39" cy="-8" rx="51" ry="46"/><ellipse cy="-50" rx="57" ry="47"/><ellipse cx="-35" cy="-45" rx="35" ry="36"/></g><g className="farm-leaves" fill="#699158" opacity=".8"><ellipse cx="9" cy="-63" rx="38" ry="29"/><ellipse cx="43" cy="-19" rx="28" ry="22"/></g></g>
      <g transform="translate(755 372)"><path d="M0 110L-5-37M-3 48L-37 0" stroke="#6e7652" strokeWidth="13"/><g className="farm-leaves" fill="#477c51"><ellipse cx="-14" cy="-35" rx="58" ry="55"/><ellipse cx="27" cy="-72" rx="47" ry="50"/><ellipse cx="-35" cy="-78" rx="44" ry="43"/></g></g>
      {/* Rice rows use reusable SVG shapes rather than separate animated DOM blades. */}
      {[0,1,2].map(row => <g key={row} transform={`translate(${25 + row * 15} ${550 + row * 35})`}><g className={`farm-rice farm-rice-${row}`}>
        {Array.from({length: 11}, (_, col) => <use key={col} href={`#${id}-rice`} x={col * 32} y={Math.sin(col) * 8} />)}
      </g></g>)}
      {/* Bangladeshi brown cow, shaded coat, dewlap, horns, split hooves. */}
      <g transform="translate(190 431)"><ellipse cx="55" cy="104" rx="86" ry="12" fill="#244d35" opacity=".25"/>
        <g fill="#895e3d"><path d="M5 42L9 96L19 99L25 45Z"/><path d="M91 43L89 96L100 97L111 38Z"/></g>
        <path d="M-8 1Q28-22 88-8Q119-1 126 27Q130 51 96 59L20 58Q-7 56-8 28Z" fill={ref('cow')}/>
        <path d="M6 37L3 96L17 99L27 43M99 43L111 96L124 96L118 29" fill={ref('cow')}/>
        <path d="M1 95H18V102H0ZM110 94H125V102H110Z" fill="#3e4935"/>
        <g className="farm-cow-tail"><path d="M-7 9Q-32 23-25 56L-30 69" stroke="#91613e" strokeWidth="5" fill="none"/><path d="M-33 65L-23 66L-28 78Z" fill="#554e37"/></g>
        <g className="farm-cow-head"><path d="M95 2Q99-30 118-27Q137-22 136 5L126 42Q110 56 104 28Z" fill="#c39967"/><path d="M111 13Q109 40 125 43L139 30" fill="#d4b583"/><path d="M116-26L108-41L113-43L124-26M131-23L140-36L145-35L139-17" fill="#e6d5aa"/><path d="M114-17Q89-32 89-16Q99-5 115-10M134-12Q156-23 154-7Q145 2 135-2" fill="#b18456"/><path d="M122-22Q141-19 142 0L150 22Q147 37 127 31L119 5Z" fill="#d6b27e"/><ellipse cx="138" cy="24" rx="13" ry="8" fill="#a67b56"/><circle cx="131" cy="-2" r="2.5" fill="#253d30"/><circle cx="143" cy="23" r="1.6" fill="#5b513a"/><path d="M112 15Q118 35 134 35" fill="none" stroke="#52634a" strokeWidth="2"/></g>
      </g>
      {/* Black Bengal goat. */}
      <g transform="translate(391 449)"><ellipse cy="65" rx="43" ry="7" fill="#244d35" opacity=".25"/><path d="M-24 14L-27 60H-20L-11 19M14 14L17 60H24L27 11" fill="#343f34"/><ellipse cy="8" rx="34" ry="22" fill="#444e3e"/><path d="M-30-1L-43-17" stroke="#47523e" strokeWidth="5"/>
        <g className="farm-goat-head"><path d="M18 7L28-28L45-27L49-5L37 15Z" fill="#374437"/><path d="M29-28Q21-48 28-49M41-27Q42-48 49-46" fill="none" stroke="#b9b697" strokeWidth="3"/><path d="M29-22L11-20L24-9M44-20L58-24L53-10" fill="#5a6750"/><path d="M41 8L42 23L32 12" fill="#354032"/><circle cx="40" cy="-16" r="2" fill="#dbcfa0"/></g>
      </g>
      <g transform="translate(405 582)"><g className="farm-hen-walk"><ellipse cy="22" rx="24" ry="4" fill="#244d35" opacity=".2"/><path d="M-6 9L-7 22M6 9L8 22" stroke="#b99154" strokeWidth="2"/><path d="M-11-6L-30-22L-25-4L-34-11L-24 8" fill="#53644a"/><ellipse cy="0" rx="21" ry="15" fill="#d9b581"/><path d="M-11-3Q14-12 11 7Q-2 15-11-3" fill="#b58c58"/><g className="farm-hen-head"><path d="M12 0Q12-30 25-27Q40-15 27 4" fill="#e4c795"/><path d="M23-26Q16-38 23-38L28-31Q34-37 35-30L32-24" fill="#a65b44"/><path d="M32-15L43-10L33-8" fill="#c2984f"/><circle cx="29" cy="-18" r="2" fill="#334332"/></g></g>
        <g className="farm-chicks"><use href={`#${id}-chick`} x="-43" y="13"/><use href={`#${id}-chick`} x="-67" y="4"/><use href={`#${id}-chick`} x="-82" y="21"/></g>
      </g>
      <g fill="none" stroke="#fae7b3" strokeLinecap="round" opacity=".5"><path d="M608 492h37m-49 5h30m-15 6h41m-27 7h14"/></g>
      <g transform="translate(648 548) scale(.7)"><ellipse rx="12" ry="4" fill="#577e58"/><path d="M-7-3q1-4 5-2l2-6 3 5 5-2q-1 7-8 7Z" fill="#f8e9da"/></g>
      <g transform="translate(670 558)"><ellipse rx="12" ry="4" fill="#537f59"/><path d="M0 0Q-10-1-9-7L-3-4Q-4-10 0-12Q4-9 4-4L9-8Q10-2 0 0" fill="#fff3dd"/></g>
      <g stroke="#5c814c" strokeWidth="3" fill="none"><path d="M465 596l-4-32m5 32l9-25m240 8l-4-30m4 30l12-23"/></g>
      <g fill="#dfd6a0" opacity=".8"><circle cx="135" cy="607" r="2"/><circle cx="152" cy="619" r="2"/><circle cx="689" cy="621" r="2"/></g>
    </svg>
  </div>;
}


