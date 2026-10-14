import {test,expect} from '@playwright/test';
import {buildHighlightRanges,nextHighlightStart,usePlayerStore} from '../client/src/stores/playerStore';
test('T3.2 highlight ranges threshold gaps and next scene',()=>{
 const ranges=buildHighlightRanges([{second:0,score:75},{second:1,score:76},{second:2,score:90},{second:3,score:20},{second:5,score:99},{second:7,score:99}]);
 expect(ranges).toEqual([{start:1,end:3},{start:5,end:6},{start:7,end:8}]);
 expect(nextHighlightStart(3,ranges)).toBe(5);expect(nextHighlightStart(7,ranges)).toBeNull();
 expect(buildHighlightRanges([])).toEqual([]);expect(buildHighlightRanges([{second:0,score:100},{score:90},{second:1,score:NaN}])).toEqual([{start:0,end:1}]);
});
test('T3.2 clip seek uses source offset and player writes time',()=>{
 const el={currentTime:0,duration:8} as HTMLVideoElement;
 const store=usePlayerStore.getState();store.register(el,20);store.seekTo(24);expect(el.currentTime).toBe(4);
 expect(usePlayerStore.getState().currentTime).toBe(20);
 store.onTimeUpdate(24);expect(usePlayerStore.getState().currentTime).toBe(24);
 store.seekTo(-1);expect(el.currentTime).toBe(0);store.seekTo(100);expect(el.currentTime).toBe(8);
 store.register(null);store.seekTo(5);expect(usePlayerStore.getState().videoEl).toBeNull();
});
