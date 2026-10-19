import {continueRender, delayRender} from 'remotion';
import blackHanSans from '../../assets/fonts/blackhansans/BlackHanSans-Regular.ttf';
import doHyeon from '../../assets/fonts/dohyeon/DoHyeon-Regular.ttf';
import gowunBatang from '../../assets/fonts/gowunbatang/GowunBatang-Regular.ttf';
import jua from '../../assets/fonts/jua/Jua-Regular.ttf';
import nanumGothic from '../../assets/fonts/nanumgothic/NanumGothic-ExtraBold.ttf';

// Bundled OFL fonts (config/fonts-lock.json) so captions look the same on every machine.
export const FONTS = {
  variety: '"VlogBlackHan", sans-serif',
  cute: '"VlogJua", sans-serif',
  sfx: '"VlogDoHyeon", sans-serif',
  serif: '"VlogGowunBatang", serif',
  dialogue: '"VlogNanumGothic", sans-serif',
};

const SOURCES: [string, string][] = [
  ['VlogBlackHan', blackHanSans], ['VlogJua', jua], ['VlogDoHyeon', doHyeon],
  ['VlogGowunBatang', gowunBatang], ['VlogNanumGothic', nanumGothic],
];

let loading: Promise<void> | null = null;

export const ensureFonts = () => {
  if (loading || typeof document === 'undefined') return;
  const handle = delayRender('Loading bundled caption fonts');
  loading = Promise.all(SOURCES.map(async ([family, url]) => {
    const face = await new FontFace(family, `url(${url})`).load();
    (document.fonts as unknown as Set<FontFace>).add(face);
  })).then(() => continueRender(handle));
};
