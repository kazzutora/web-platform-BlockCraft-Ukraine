import type { SVGProps } from "react";
import { Bell } from "pixelarticons/react/Bell.js";
import { Blocks } from "pixelarticons/react/Blocks.js";
import { Bookmark } from "pixelarticons/react/Bookmark.js";
import { Check } from "pixelarticons/react/Check.js";
import { ChevronDown } from "pixelarticons/react/ChevronDown.js";
import { ChevronLeft } from "pixelarticons/react/ChevronLeft.js";
import { ChevronRight } from "pixelarticons/react/ChevronRight.js";
import { ChevronUp } from "pixelarticons/react/ChevronUp.js";
import { Close } from "pixelarticons/react/Close.js";
import { Copy } from "pixelarticons/react/Copy.js";
import { Download } from "pixelarticons/react/Download.js";
import { ExternalLink } from "pixelarticons/react/ExternalLink.js";
import { Eye } from "pixelarticons/react/Eye.js";
import { EyeOff } from "pixelarticons/react/EyeOff.js";
import { Filter } from "pixelarticons/react/Filter.js";
import { Flag } from "pixelarticons/react/Flag.js";
import { Gamepad } from "pixelarticons/react/Gamepad.js";
import { Globe } from "pixelarticons/react/Globe.js";
import { Heart } from "pixelarticons/react/Heart.js";
import { Home } from "pixelarticons/react/Home.js";
import { Image } from "pixelarticons/react/Image.js";
import { InfoBox } from "pixelarticons/react/InfoBox.js";
import { Link } from "pixelarticons/react/Link.js";
import { Lock } from "pixelarticons/react/Lock.js";
import { Login } from "pixelarticons/react/Login.js";
import { Logout } from "pixelarticons/react/Logout.js";
import { Menu } from "pixelarticons/react/Menu.js";
import { Moon } from "pixelarticons/react/Moon.js";
import { MoreHorizontal } from "pixelarticons/react/MoreHorizontal.js";
import { Pencil } from "pixelarticons/react/Pencil.js";
import { Plus } from "pixelarticons/react/Plus.js";
import { Reload } from "pixelarticons/react/Reload.js";
import { Search } from "pixelarticons/react/Search.js";
import { Server } from "pixelarticons/react/Server.js";
import { SettingsCog } from "pixelarticons/react/SettingsCog.js";
import { Share } from "pixelarticons/react/Share.js";
import { Star } from "pixelarticons/react/Star.js";
import { Sun } from "pixelarticons/react/Sun.js";
import { Trash } from "pixelarticons/react/Trash.js";
import { Trophy } from "pixelarticons/react/Trophy.js";
import { Upload } from "pixelarticons/react/Upload.js";
import { User } from "pixelarticons/react/User.js";
import { Users } from "pixelarticons/react/Users.js";
import { WarningDiamond } from "pixelarticons/react/WarningDiamond.js";

import { cn } from "@/lib/cn";

type SvgIcon = (props: SVGProps<SVGSVGElement>) => React.JSX.Element;

/** Filled pixel star for ratings (pixelarticons has only the outline). */
const StarFilled: SvgIcon = (props) => (
  <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor" {...props}>
    <path d="M11 1H13V3H15V7H23V11H21V13H19V16H21V22H16V20H14V18H10V20H8V22H3V16H5V13H3V11H1V7H9V3H11Z" />
  </svg>
);

const icons = {
  bell: Bell,
  blocks: Blocks,
  bookmark: Bookmark,
  check: Check,
  "chevron-down": ChevronDown,
  "chevron-left": ChevronLeft,
  "chevron-right": ChevronRight,
  "chevron-up": ChevronUp,
  close: Close,
  copy: Copy,
  download: Download,
  "external-link": ExternalLink,
  eye: Eye,
  "eye-off": EyeOff,
  filter: Filter,
  flag: Flag,
  gamepad: Gamepad,
  globe: Globe,
  heart: Heart,
  home: Home,
  image: Image,
  info: InfoBox,
  link: Link,
  lock: Lock,
  login: Login,
  logout: Logout,
  menu: Menu,
  moon: Moon,
  more: MoreHorizontal,
  pencil: Pencil,
  plus: Plus,
  reload: Reload,
  search: Search,
  server: Server,
  settings: SettingsCog,
  share: Share,
  star: Star,
  "star-filled": StarFilled,
  sun: Sun,
  trash: Trash,
  trophy: Trophy,
  upload: Upload,
  user: User,
  users: Users,
  warning: WarningDiamond,
} satisfies Record<string, SvgIcon>;

export type IconName = keyof typeof icons;

type IconProps = Omit<SVGProps<SVGSVGElement>, "name"> & {
  name: IconName;
  /** Pixel icons are drawn on a 24 px grid; multiples of 24 stay crisp. */
  size?: 16 | 24 | 48;
  /** Accessible name; without it the icon is decorative. */
  label?: string;
};

export function Icon({ name, size = 24, label, className, ...props }: IconProps) {
  const Svg = icons[name];
  return (
    <Svg
      width={size}
      height={size}
      shapeRendering="crispEdges"
      focusable="false"
      className={cn("shrink-0", className)}
      {...(label ? { role: "img", "aria-label": label } : { "aria-hidden": true })}
      {...props}
    />
  );
}
