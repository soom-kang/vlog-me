import {continueRender, delayRender} from 'remotion';
import blackHanSans from '../../assets/fonts/blackhansans/BlackHanSans-Regular.ttf';
import cormorant from '../../assets/fonts/cormorantgaramond/CormorantGaramond-Variable.ttf';
import cormorantItalic from '../../assets/fonts/cormorantgaramond/CormorantGaramond-Italic-Variable.ttf';
import doHyeon from '../../assets/fonts/dohyeon/DoHyeon-Regular.ttf';
import gowunBatang from '../../assets/fonts/gowunbatang/GowunBatang-Regular.ttf';
import jua from '../../assets/fonts/jua/Jua-Regular.ttf';
import nanumGothic from '../../assets/fonts/nanumgothic/NanumGothic-ExtraBold.ttf';
import nanumPen from '../../assets/fonts/nanumpenscript/NanumPenScript-Regular.ttf';

// Bundled OFL fonts (config/fonts-lock.json) so captions look the same on every machine.
export const FONTS = {
  variety: '"VlogBlackHan", sans-serif',
  cute: '"VlogJua", sans-serif',
  sfx: '"VlogDoHyeon", sans-serif',
  serif: '"VlogGowunBatang", serif',
  dialogue: '"VlogNanumGothic", sans-serif',
  pen: '"VlogNanumPen", cursive',
  latin: '"VlogCormorant", "VlogGowunBatang", serif',
};

const SOURCES: [string, string, FontFaceDescriptors?][] = [
  ['VlogBlackHan', blackHanSans], ['VlogJua', jua], ['VlogDoHyeon', doHyeon],
  ['VlogGowunBatang', gowunBatang], ['VlogNanumGothic', nanumGothic], ['VlogNanumPen', nanumPen],
  ['VlogCormorant', cormorant, {weight: '300 700'}], ['VlogCormorant', cormorantItalic, {weight: '300 700', style: 'italic'}],
];

let loading: Promise<void> | null = null;

export const ensureFonts = () => {
  if (loading || typeof document === 'undefined') return;
  const handle = delayRender('Loading bundled caption fonts');
  loading = Promise.all(SOURCES.map(async ([family, url, descriptors]) => {
    const face = await new FontFace(family, `url(${url})`, descriptors).load();
    (document.fonts as unknown as Set<FontFace>).add(face);
  })).then(() => continueRender(handle));
};
