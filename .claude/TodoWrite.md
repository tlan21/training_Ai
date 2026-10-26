# TodoWrite — T1.4 ASR-only gold-reference intake

## Task hiện tại — DONE: mở lại trang ASR review (2026-10-26)

- [x] Khởi động HTTP server PID 22368, bind 127.0.0.1:8891, phục vụ thư mục D:/data_training_ai/asr_domain_expansion_v2_20261022. Trang /asr_review_v2/index.html trả HTTP 200; đã mở lại tab Chrome, hiển thị Chốt lời chuẩn ASR và tiến độ 7/60 lưu sẵn. Không sửa nội dung review hoặc chạy training; chưa kiểm tra lại phát audio/video trong lần khởi động này.

## Task hiện tại — DONE: T1.4 chép lời nháp60/60 +trang nghe duyệt; HUMAN REVIEW PENDING (2026-10-22)

- [x] Sau người dùng bật fileURLs, Chrome2 chọnWAV được. Dockerengineoff; giữscopeexpansion_v2/40nhãncũ/validation/test/models.
- [x] Chẩnđoán AutoDetect8clip (7/8lặp), MP4AutoDetect vẫnlặp. Giữriêngv2/pilot, khôngghépnhãn. Mộtpilot chọnnhầmFinnish đượcghiINVALID_UI_SELECTION. Batchchínhv3 dùngoptionEnter +checkUIvalue trước từngjob:base291MB/Multilingual/Transcribe/unquantized,6English/54Vietnamese theo nguồn, chưa xácminh speechlanguage.
- [x] Đủ60/60newdrafts,180rawTXT/JSON/SRT81.057bytes +60receipts; kiểmTXT/JSON/text/segments/hash/source PASS. CUA UI tuần tự; Chromedownloadeventtimeout nên thu nativeDownloadsfilesvới receipt rõ binding/khônggiảIDprovider. 25clip cócờ:14timingoutside,8nullend,3short,3repeat;2nhóm9clip trùnglờimáy cầnnghe. Tấtcảunverified/noautomaticgold.
- [x] ActualASR-onlyreviewpage60cards/WAV+MP4/nguồnnháp/protocolstorageexportriêng/ngônngữngheđược; tên/ngônngữblank/0checks. Exportthực tế60records/test_fixturefalse/noapprovals/training_readyfalse PASS. Desktop1440/mobile390/ảnhfields/nooverflow/padding12px +playbackWAV/video PASS, khôngclaimnghe. Oldfixtureguards táchTEST_ONLY. Viewportreset/tabdeliverable. http://127.0.0.1:8891/asr_review_v2/index.html, serverPID16000 bindloopback.
- [x] Final104Python tests +JSsyntax/selfchecks +Go vet/test/build +CMS tsc/Vite +Client tsc/Next/lint14pages PASS.180output/120media/9source/25protectedfiles unchanged; UIactualverification/report/READMEs/manifests lưu đủ. @docs/T1.4_asr_expansion_transcription.md.
- [x] DRAFT CONVERSION +REVIEW PREPARATION DONE.0humanlabels,notraining/Kaggle/deployment/gatechange. Khôngđòi chốt40clipcũ. Actualreview seeddraft trongDownloads/asr_expansion_review_v2.json vàreviewfolder, chưaphảinhãnchuẩn.

Next safe task:người dùng nghe/sửa/xácnhận hoặc ghi lýdoloại, ưu tiên9duplicate/25flagged, rồi xuấtJSONthật. Sauđó strictintake giữmachine-assisted provenance/coverage/train-onlyvocab/CTC/splitguards trước recipe khác. Human review chưahoànthành; khôngclaimmodelquality/WER hoặc tựtrain/deploy.

## Task hiện tại — DONE: T1.4 audit lỗi train và chuẩn bị media bổ sung (2026-10-22)

- [x] Đọc startup/AI training skill/plan và run500. Audit đúng 30 train đã duyệt; giữ 10 validation, test, kênh loại trừ và các guard. Không rerun training hoặc đánh giá lại test.
- [x] Audit S/D/I + cue lexicon có định nghĩa/hash. Parent133 macro WER/CER 91,5664%/48,5375%; rejected last134 79,5772%/38,9247% trên chính train đã học. Không claim generalization/promotion. English cues chỉ ONLINE×3/CPI×1; mã pháp luật đầy đủ theo regex: 0. Numeric strict-surface 0/88 khớp, không suy thành không hiểu mọi số. Dấu câu mép token chỉ giải thích 42/2.259 hoặc 75/1.989 substitutions.
- [x] Tải 9 nguồn public CC từ 9 kênh mới, ngoài mọi nguồn/kênh domain và frozen test cũ. Bản tải nguồn + metadata/provenance giữ D:/data_training_ai/asr_domain_expansion_v2_20261022/raw/youtube. Chuẩn bị 60×20s WAV/MP4 =20 phút, không chồng thời gian/trùng PCM với 70 audio cũ. Nội dung/ngôn ngữ/speaker/code-switch chưa nghe xác minh; 0 nhãn mới được duyệt, không pseudo-gold.
- [x] Độc lập kiểm 9 raw/60 WAV/60 MP4 hashes/durations/formats; 9/9 nguồn phát thử headless mute PASS. 23 protected files của supplement +24 audit giữ nguyên. Shared ASRDataset từ chối thực tế manifest 60 transcript rỗng. README/REVIEW_QUEUE và verification JSON đã lưu trên D:.
- [x] 194 Python tests + Go vet/test/build + CMS tsc/Vite + Client tsc/Next/lint PASS. Metadata normalization audit đã ghi rõ domain/NFC/uppercase/whitespace, giữ dấu câu/số; không đổi điểm. Không live Docker/E2E/VRAM vì engine off.
- [x] Báo cáo @docs/T1.4_asr_train_error_audit.md; manifests @data/manifests/asr_train_error_audit.json +asr_domain_expansion_v2.json. Không train/upload/deploy mới; active weights/nhãn cũ/guard và HOLD PROMOTION giữ nguyên.

Next safe task: tạo bản nháp chép lời và nghe duyệt batch mới 60 clip, ưu tiên xác minh English/code-switch/mã/số/địa danh; giữ machine-assisted provenance. Chỉ sau nhãn đã duyệt +train-only vocab/CTC checks mới chuẩn bị training tiếp. Không yêu cầu duyệt lại 40 clip cũ; pilot 20 phút chưa chứng minh coverage đủ.

## Task hiện tại — DONE: GPU500/output verified, giữ parent133 / HOLD PROMOTION (2026-10-22)

- [x] Packet/22protectedhashes/sourcebundle/staging PASS; live3oldinputsprivate/currentversions1/2/1, cácjobcũ COMPLETE. Newdatasetprivatev1 tạo thànhcông, không ghiđèdataset/jobcũ.
- [x] Submit đúng1job traininghighlight/asr-domain-replay-guarded-v1 version1; liveRUNNING TeslaT4. Authoritative pulledmetadata PRIVATE/GPU/InternetOFF/4inputs/runnertextparity PASS. @data/manifests/asr_domain_replay_training.json; chưa có kết quả chất lượng.
- [x] Kiểm trạng thái live2026-10-22: cùngjobv1 COMPLETE. Không gửi thêmjob.
- [x] Tảioutputs-v1/log/best/last/report; độc lậpkiểm500steps/5guards/selected0/133vocab/config/head/parenttensors equality/2126testrefs mỗi model+predictions/editdistances/aggregates/4mathsanities/22protectedhashes PASS. All5updatedcheckpoints rejected:domainWER91.2610→best83.8031(step400), nhưngVIVOSWER+0.1232pp/FLEURSWER+2.2180pp ở400. `best.pt`giữparent133, `last.pt`134step500rejected, không cóweightsstep400. Khôngđổi guard/nhãn/test/deploy.
- [x] ActualT4/Torch2.11CUDA/fp16;train+eval18.0942min(excludesstaging/initialbaseline),peakallocated1.1166/reserved2.5039GiB<8. Không suy thànhinference6model4GiB. SourcefileSHA/modelweights/reviews/ratings/frozen10 unchanged. Plot21losspoints/5valpoints rendered+visualchecked; @docs/T1.4_asr_domain_replay_training.md; metricsJSON vàcurvePNG trênD:.
- [x] Collectorfix: parseKaggleJSONeventdata để giải mã\\u003c trước4sanitymarkerchecks; regressionFAILbefore/PASSafter, khôngrerunGPU.180Python tests +Go vet/test/build +CMS tsc/Vite +Client tsc/Next full lint14/14 PASS. No liveDocker/E2E vìengineoff.

Changed: completedsinglev1collection/verification/report/plot +logreaderfix/tests. Verified:500updates/22protectedfiles/weightsfallback/testrefs+metrics/4sanities/180tests/builds PASS. Contract touched:noAPI/architecture/loss/servingweights changes. Next safe task:auditerror/coverage trênapprovedtrain +planadditionaldiversehuman-reviewedtrainaudio outsidefixedvalchannels; khônglặpsamejob/giảmguard/chọntheo test. FullAIgate/human1.6/5 unchanged; no promotion.

## Task hiện tại — DONE: T1.4 domain-adaptation recipe/packet, NOT TRAINED (2026-10-21)

- [x] Đọc startup/AI skill/ASR model-data-evaluation/plan/sharedtrainer/packet/staging/tests. Scope: sharedtrainer optionaldomainrecipe +tests, newprivatepacket/runner/docs; giữlegacy2/3source,133parent/134head/trainonly, fixed10 vàtestscũ.
- [x] Recipe asr-domain-replay-v1:parentd03ef0…/134head/seed1337/500updates/eval100/LR3e-5/batch4×4; VIVOS.4/FLEURS.3/EN.2/domain.1. All4WER/CERnonregression +strictdomainWER/CER/meanWER improvement. Original133fallback saved/reloaded withcorrectvocab ifnoeligible; rejectedlast khôngreplacebest. Legacy2/3source paths giữ nguyên.13newdomain tests gồm actualdriverCPU-stub acceptance/rejection; noGPUqualityclaim.
- [x] Newprivatepacket D:/data_training_ai/asr_domain_replay_v1_20261021/kaggle_dataset +runner/metadata.19,280audioSHA/40domainZIP/15,110trainroundtrip/15,106retained+same4exclusions/11Mel loader checks/sourceweights/frozen10/currentsourcebundle PASS. Actualparent133→134 inRAM giữexactoldtensors,finite; noexpandedcheckpointwrite. Canonicalreferenceidentity fixesWindowslineendingdependency whilefrozenbytes unchanged; incompleteattemptarchivedseparately.
- [x]157Python tests +Go vet/test/build +CMS tsc/Vite +Client tsc/Next full lint14/14 PASS. Protectedfiles unchanged. Packet/staging/preflight evidence +@docs/T1.4_asr_domain_replay_preparation.md +@data/manifests/asr_domain_replay_preparation.json. Dockerengine unavailable; no liveHTTP/E2E/CUDA/remoteupload/job/deployment.

Changed:sharedtrainer/wrapper optionaldomainrecipe,tests,newpacket/runner/report. Verified:157tests/actualdata/audio/loader/vocab/headprefix/guards/builds PASS. Contract touched:noAPI/architecture/loss/productionweights changes. Next safe task:uploadnewprivatesupplement+one500-stepKagglejob,collect/verifyresultsbeforepromotion.15mintrain/5minval small, fixed10 isdevelopment/notindependenttest; labelorigin human-reviewedexternalASR. FullAIgate/human1.6/5 unchanged.

## Task hiện tại — DONE: nhập đủ40nhãn và chấm fixed10 (2026-10-21)

- [x] Downloads/asr_verbatim_domain_v1.json mới50690bytes lúc14:12, SHAa1ecca1bc0cd…; snapshot received_a1ecca1bc0cd nguyênbyte.40/40transcript_verified=true/noexclude; strictimport giữmachine-assistedorigin,30train/10val,khôngpending.2valtextđổi/30trainitems unchanged.
- [x] Freeze đủ10val/frozen_validation.json vàchấm3checkpoint từcachedprediction cóhashnguồn. MacroWER/CER%:active96.1333/55.8295,parent91.6021/47.4726,three_source94.5083/49.3379. Independentfull-matrix editdistance kiểmtra30predictions/macro+corpus+counts PASS;15protectedhashes/media/source/weights/snapshot PASS. Parent tốt hơn nhưngmọimodelvẫnrấtkém; HOLDPROMOTION.2train? ngoài133vocab nên training_ready=false;134train-onlypreflight trướcvẫnápdụng vìtrainitemsunchanged. Khôngtrain/deploy/summarytarget.

Changed:actual40-referenceintake/frozen10/scores/report. Verified:strictimport+independentmetric/cachedbinding/15protectedhashes;16targetedtests PASS, appbuilds khônglặpvìdata/docs-only (bướcfixUItrướcđãPASS). Contract touched:noAPI/code/weights/productionvocab changes. Next safe task:chuẩnbị bounded domain-adaptation recipe từparent133 +proposed134/replay/validationguards trướcGPU; nhãnđãđủ, khôngyêucầuchốt3đoạnlạinữa. @docs/T1.4_asr_verbatim_results.md. FullAIgate/human1.6/5 unchanged.

## Lịch sử — yêu cầu xuất sau khi người dùng xác nhận hết (đã nhận file mới)

- [x] Người dùng báo đã xác nhận hết. Kiểm Downloads: chỉ có bản37xácnhận cũ vànext_draft; chưa có exportmới. CUAgetState lỗi `failed to write kernel assets ... os error3`; không có CDP9222/9223. Không truy cập được trạng thái/chỉnh sửa mới trong trình duyệt của người dùng; không tự dựng40xácnhận từfilecũ vì có thể mất lời chép vừa sửa.
- [x] Người dùng đã xuấtfilemới14:12; đã nhận/kiểm/import/chấm ởtaskhiệntạiphíatrên. Không tựdựng40xácnhận từfilecũ.

## Task hiện tại — DONE: thông báo lỗi xác nhận ASR (2026-10-21)

- [x] Đọc template/caller render/browser regression/importer. Export37approved có3exclude_reason còn nội dung; guard chặn đúng nhưng thông báo chung không chỉ ra trường cần sửa.
- [x] Tách4thôngbáo đúngnguyênnhân/tựfocus+aria-invalid ởôcần sửa; lýdochưachốt chỉxóathủcông saukhiđãsửaaudio, ghi chú cũ giữnguyên. Newbrowsertest FAIL trướcfix/PASS saufix;4viewports/13playback/keyboard/200%text/filefallback +real37approvalresume desktop/mobile PASS; screenshot mobile đãđốichiếu khôngoverlap/overflow. Python16tests,Go vet/test/build,CMS tsc/Vite,Client tsc/Next full lint14/14 PASS.15protectedhashes/packet/37labels/localStoragekey unchanged. Cập nhật index.html đangphụcvụ; bảnHTMLcũ giữởindex_before_confirmation_errors.html, preparation.json giữbằngchứng lịch sử. @docs/T1.4_asr_verbatim_intake.md.

Changed: validation error messages/focus +browserregression +servedHTML. Verified: checks ởtrên; khôngtựapprove/xóareason/đổinhãn. Contract touched:noAPI/importer/model changes. Next safe task: người dùng nghe/sửa/xóalýdochưachốt của3validation rồi xácnhận vàxuấtJSONmới; chưaWER/train/promotion/liveDocker.

## Export theo yêu cầu — DONE (2026-10-21)

- [x] Xuất `C:/Users/PC/Downloads/asr_verbatim_domain_v1_next_draft.json` và bản sao trong `asr_verbatim_v1/followup_009840ca1e6a/`. Đưa2đềxuấtsửachữ vào bảnnháp, giữ nguyên37xác nhận/40IDs/nguồn/ghi chú;3validation vẫnunverified. Strictvalidator xác nhận30train/7valapproved,3valpending;2bảnbyte-identical/SHA6ba0f9781231…, snapshotgốc unchanged. Khôngtraining/chấmđiểm/buildapp (dataexport-only).
- [ ] Người dùng nghe/sửa/chốt3validation trước khi xuất bảnđãduyệt để chấm đủ10mẫu. Bảnnext_draft không phải xác nhậnmới/gold40.

## Lịch sử — chuẩn bị preflight

Task hiện tại: **PREPARATION DONE — T1.4 TRAIN-ONLY PREFLIGHT; 3 VALIDATION CHỜ CHỐT THEO AUDIO** (2026-10-21). Đã lưu2đề xuất sửa chữ/3clip riêng, không tựbậtverified. Đề xuấtvocab134 thêm? chỉ từ30train,30/30roundtrip/actualaudio/CTC PASS,15phútaudio; sharedexpand_head kiểmtratrongRAM giữ nguyên133IDs/toànbộweightscũ, rowmới chưa học, khônglưucheckpoint. 39tests PASS/15protectedhashes unchanged. Câu hỏi lờiđúng của3clip đãgửi; chưa đủ10validation/chưa training/chấm điểm/promotion.

- [x] Startup/AI instructions/oneplan/review/intake/UIcallers đọc; toolinventory không có audio-input/listening/transcription tool. Docker engine unavailable. Kiểm exportmới và giữbảnsnapshot cũ.
- [x] ASR-only verifier/import/scorer giữmachine-assisted origin/source/media/feedback; rawvalidation labels khôngquaencoder, trainOOV báo riêng; no partialvalidation denominator/QAfixtures accepted. Freeze10val onlywhencomplete; khôngđoWER/train khi chưa cógold.
- [x] Seedactual40transcripts/39edits/33feedback/name, no summaryrequirement,10valfirst; ownstoragekey, originalbrowserdrafts/review/weights/test unchanged. http://127.0.0.1:8890/asr_verbatim_v1/index.html vàlocalfilefallback phátvideo được.
- [x] 182Python tests +Playwright1440/390/375/844/landscape/13playbacks/200%text/reducedmotion/keyboard/nooverflow +visualQC; Go vet/test/build +CMS tsc/Vite +Client tsc/Next14/14 PASS. Actualseedintake0/0approved,nullscores,noaccepted/frozenfiles; không suy trạngtháiasrcontent từcombinedchecks cũ. @docs/T1.4_asr_verbatim_intake.md; @data/manifests/asr_verbatim_preparation.json vàasr_verbatim_intake.json.
- [x] Nhận file Downloads mới50878bytes, snapshot received_009840ca1e6a; strict importer chấp nhận37xác nhận riêngASR, đủ40IDs/source/media/feedback. Xuất accepted_asr_009840ca1e6a/asr_train.json (30) vàasr_val.json (7); giữ nguồn human_reviewed_external_asr, không nhập summary. 16tests PASS;15protected hashes và snapshot byte-parity PASS. Không tạo frozen_validation hoặc điểm từ7/10mẫu.
- [x] Bước tiếp theo: followup_009840ca1e6a/CORRECTIONS_REVIEW.md +correction_proposals.json (2orthographicproposals/3unverifiedclips, protocolkhôngnhậpnhãndược). Đềxuấtvocab134/proposed_vocab_134.json từapprovedtrainonly,2nguồn?; sharedstrictloader30labels/roundtrip30/audio16kmono/nonzero/SHA30/CTC30 PASS. Sharedexpand_head CPU/RAMonly giữnguyênoldweights/133IDs, khôngclaimsoftmaxparity/rowmớiđãhọc. 39tests+15protectedhashes PASS; @data/manifests/asr_domain_followup_preflight.json; @docs/T1.4_asr_domain_followup.md. Không đổiappcode/weights/productionvocab/exportcũ; noappbuildrerun vìdata/docs-only.
- [ ] Hoàn tất3validation dom_wzKzkenrYew_1 / dom_f7VbxhaVtfk_2 / dom_wYRFi4-KWek_1: sửa lời theoaudio, xóa lýdo chưa chốt saukhi đãsửa, xácnhận lại vàxuấtJSON. Sauđó chấm đủ10mẫu; xửlý train-only vocabulary coverage cho dấu? ở2nhãn, không tựxóa kýtự. Chưa training/promotion.

Changed:2đềxuấtsửachữ/3clip +train-onlyvocab134preflight/report;37approvedlabels giữnguyên. Verified:39tests +30audio/labelroundtrip/CTC/headprefix/15protectedhashes PASS. Contract touched:noAPI/appcode/model/productionvocab change; chỉcandidatevocabproposal riêng. Next safe task:nghechốt3validation rồi chấm3checkpoint; actualheadrow? cầntrainingrecipe riêngtrước khi có thể dùng. Không tựnhậnngheaudio/semantic audit; fullAIgate/human1.6/5/activeweights unchanged. @docs/T1.4_asr_domain_followup.md.

## Lịch sử — three-source real-audio paired diagnostic

Task hiện tại: **DONE — TRAINING OUTPUT VERIFIED / REAL-AUDIO PAIRED CHECK / HOLD PROMOTION** (2026-10-21). KaggleCOMPLETE2000updates/outputdownload/guards/checkpointSHA verified; child05713a... selected2000. Diagnostic40existingdomainclips:120freshoutputs,80/80baselinecacheparity,0empty/timingvalid,33feedback preserved. Không promote/đổi review/gán gold hoặc đoWER từunapprovedlabels.

- [x] Thu outputs-v1 vàverify actual2126test/sourcecounts/rawrefs/editdistances/aggregates/historyguard/beststep/133head/parenthash/VRAM/12protectedfiles; trainingtask DONE, no deployment.
- [x] 3variants×40clips/120freshoutputs via productionASR,CPUFP32/Torch2.13/35.609s; active40/40 +parent40/40textcacheparity,0empty/validtiming,80media hashes/protectedfiles unchanged. ComparisonJSON/plaintext +33feedback/30train10val partition preserved; real-videoWER/CERnull.
- [x] 139Python tests +Go vet/test/build +CMS tsc/Vite +Client tsc/Next14/14 PASS. @docs/T1.4_asr_three_source_real_audio.md; @data/manifests/asr_three_source_real_audio.json; D:/data_training_ai/asr_three_source_v1_20261020/real_audio_comparison_20261021. Trainingloss/valplot rendered/inspected; metricsraworiginals preserved.

Changed: verifiedoutputcollection +isolated3model realaudio runner/tests/comparisons/report. Verified:2126pairedtest/source refs/editdistances/guards/checkpointSHA/139tests/120realoutputs/cache/media/builds PASS. Contract touched:noAPI/model architecture/loss/133vocab/servingweights changes. Decision:HOLDPROMOTION; EnglishmacroWER113.3507→103.0843%,FLEURStest53.6727→53.7801%,VIVOS32.9727→32.5731%. Next safe task:approved verbatim/audio-backed English/code-switch/legal/number/name ASRdata/reference with preservedreviewprovenance, no identicalrerun/testtuning/ASR-as-goldMiniGPTtargets. FullAIgate/human1.6/5 unchanged; no liveHTTP/GPUinference/3seedproof.

## Lịch sử — three-source Kaggle training

Task hiện tại: **DONE — GPU RUN / OUTPUT VERIFIED / NOT PROMOTED** (2026-10-20). User yêu cầu bước tiếp theo sau verified3sourcepacket. Kiểm hash/job state, upload newPRIVATEsupplement, submit đúng1candidate2000updates, collect/verify actualoutputs. Giữ weights phục vụ/frozenrefs/review; không promote tự động.

- [x] Packet/12protectedfiles/runner hashes verified; existinginputs private asr-robust-humanv2/vivos-asrv1 unchanged, allpriorjobs COMPLETE. Uploaded NEWPRIVATE traininghighlight/asr-three-source-v1 version1, statusready; no overwrite olddatasets.
- [x] Submitted đúng1job version1. Kaggle canonicalslug follows title: https://www.kaggle.com/code/traininghighlight/asr-three-source-guarded-v1 (requestedai-core-asr-three-source-v1 was not actualslug; metadata/builder corrected, no duplicate push). Pulledauthoritative metadata confirms PRIVATE/GPU/internetOFF/3inputs and submittedsource parity. Latest observed QUEUED; chưa bắt đầu GPUtraining/đoWER.
- [x] Theo dõi tới terminal, tải logs/report/weights vềD:, kiểm counts/hash/guards/math/VRAM và cập nhật kết quả thật; nếu lỗi thì diagnose/fix routine runtime issue trong cùngscope.
- [x] 132Python tests including10newcollector checks +Go vet/test/build +CMS tsc/Vite +Client tsc/Next14/14 PASS. Collector checks actualper-domain guards/beststep/testrefs/counts/editdistances/aggregates/checkpointhash/parent/133vocab/VRAM/protectedfiles and updatesreport/Todo/plan only afterverifiedCOMPLETE. Failurekeepsdiagnosispending; no autopromotion/resubmission.
- [x] ActualGPUcompletion/outputquality report pending. Backgroundwatcher: dist/kaggle/kernel-asr-three-source/collect_run.py; logs D:/data_training_ai/asr_three_source_v1_20261020/monitor.log +monitor.err.log. State @data/manifests/asr_three_source_training.json; finaloutputs targetedoutputs-v1. Do not start another job whilethisoneQUEUED/RUNNING.

Actual result: selected_step=2000, recommendation=True, baseline_retained=False. Output D:/data_training_ai/asr_three_source_v1_20261020/outputs-v1; @docs/T1.4_asr_three_source_training.md. Activeweights/12protectedfiles unchanged; fullAIgate/human1.6/5 unchanged.

## Lịch sử — three-source fine-tune recipe/staging

Task hiện tại: **DONE — THREE-SOURCE RECIPE / PACKET / LOCAL STAGING VERIFIED** (2026-10-20). Candidate133 +VIVOS/FLEURS/MiniLibriSpeech,2000steps/seed1337,40/40/20source sampling, per-domain non-regression WER/CER và strictEnglishWER/meanWER improvement.19240audio SHA/staging +9source/split loader checks PASS. Chưa upload/submit/fine-tune/promote.

- [x] Startup/AI training skill/model-data-evaluation ASR sections/plan/callers/legacywrapper đọc; branch phase1-ai-core, Docker engine unavailable.
- [x] Sharedtrainer nhận recipe3source riêng, legacy2source vẫn hoạt động; all-domain WER/CER guards +strictEnglish/meanWER improvement, test chỉ evaluate sau selection. Tests chạy đến cuối training loop xác nhận giữ step0 nếu không eligible, eligiblebest không bị last.pt ghi đè; không đổi architecture/loss/vocab.
- [x] D:/data_training_ai/asr_three_source_v1_20261020/kaggle_dataset chứa supplement Englishaudio/code/recipe/source133/vocab/manifest/metadata/README hashes; tái dùng2oldprivate audio datasets. Full19240files stage/SHA trênE:/traning_ai/data/processed/asr_three_source_stage_v1,15076retainedtrain/4oldCTCexclusions,2034val/2126test, sourceweight masses40/40/20,9audio→mel loader checks PASS.3val/7testOOVreferences giữ nguyên;12protectedfiles/oldlabels+splits unchanged.
- [x] 122Python tests gồm gradient/ownAdamW/CTC/ASRoverfit +newguard/recipe/source-sampling/staging/autoextracted/hash-failure tests PASS. Go vet/test/build,CMS tsc/Vite,Client tsc/Next14/14 PASS. @docs/T1.4_asr_three_source_preparation.md; @data/manifests/asr_three_source_preparation.json; D:preflight.json/staging_check.json.

Changed: sharedtrainer optional3source recipe, sharedKaggle wrapper/staging, separate frozenpacket/newkernel metadata/tests/report. Verified:122tests/19240audioSHA/9loaders/sampling/CTC/12protectedhashes/builds PASS. Contract touched:no API; model/loss/133vocab unchanged. Next safe task:upload newPRIVATEsupplement and submit singleguarded2000update GPUcandidate; collect/verifyoutput before any promotion. No remoteKaggle/CUDA/real-fine-tune/EnglishWER/liveHTTP check, Docker engine off. Read-English/code-switch/legal gaps/27.32h<30h/fullAIgate/human1.6/5 unchanged.

## Lịch sử — supervised English data preparation

Task hiện tại: **DONE — ENGLISH SUPERVISED DATA PREPARED / NOT TRAINED** (2026-10-20). Mini LibriSpeech đã tải/kiểm đủ2608audio; train1519/5.310743h, val580/0.977111h, test509/1.058710h. Giữ133IDs/weights/reference/review; audit790oldVietnamese replay candidates, không tự xác nhận40Whisper review hoặc train/promote model.

- [x] Startup/AI training instructions, plan T1.4, shared preparation/training helpers và disk budget đã đọc; Docker engine chưa kết nối được.
- [x] Hai nguồn chính thức/raw trênD:, published MD5 +SHA256,2608FLAC16k mono/finite/nonzero/paired; speaker/chapter/ID/audioSHA/exacttext disjoint. dev-clean-2 chia speaker val/test seed1337 trước eval, không đổi testViệt cũ.
- [x] 1519newtrain roundtrip/CTCfeasible,0OOV cả3split,133vocab byte-identical/candidateprefix unchanged.790oldVI keyword replay candidates (700numeric/44place/36compound/11legal/0selectedacronyms; overlap); không coi lànewlabels/domainverified.12protected hashes vàprepared hashes PASS.
- [x] 101Python tests +actual3split audio→mel/loaders +Go vet/test/build +CMS tsc/Vite +Client tsc/Next14/14 PASS. @docs/T1.4_asr_english_preparation.md; @data/manifests/asr_english_preparation.json; D:/data_training_ai/asr_english_v1_20261020/preflight.json vàintegration_check.json.

Changed: source archives/audio/English manifests+vocab/oldVI replay list/preparation script+tests/docs. Verified:101tests/actualaudio+labels+hashes/builds PASS. Contract touched:no productionAPI; new data provenance recorded. Next safe task:3source recipe/staging starting candidate133 with per-domain validation guard/test freeze; current2source trainer is not compatible unchanged. Không train/Kaggleupload/promote/GPU/EnglishWER/liveHTTP; code-switch/legal gold gaps và30h target chưa đạt, fullAIgate/human1.6/5 unchanged.

## Lịch sử — lossless ASR label encoding

Task hiện tại: **DONE — STRICT ASR LABEL ENCODING / PREFLIGHT VERIFIED**. User yêu cầu bước tiếp theo sau audit. Đã sửa sharedCharVocab để reject ký tự không hỗ trợ, validate training labels trước audio/GPU, giữ rawheld-out reference đầy đủ cho evaluation và ghi rõ lossless label conventions. Không đổi vocab IDs/head/weights/test, không train mới; chưa claim acoustic quality cải thiện.

- [x] Startup/AI plans + ASR sections + toàn bộ callers củaCharVocab/ASRDataset/ReferenceASRDataset đọc; giữ working changes cũ. Docker engine không kết nối được.
- [x] CharVocab.encode raises ValueError thay vì bỏ ký tự; ASRDataset constructor validate toàn bộ train labels/path trước audio. SharedReferenceASRDataset+collator dùng cho generaltrainer và robustness evaluator; rawOOV reference vẫn được chấm, cấm train/augment qua loaderreference. Không thay đổi valid symbol IDs hoặc output head.
- [x] Actual133symbol preflight:13561/13561train roundtrip; giữ13557CTCfeasible/4existing exclusions.10567legacyVIVOS train còn hợp lệ; active93 trênmixed train dừng đúng.3val/7testOOVlabels giữ nguyên; diagnosticreview40active/3candidate rejected, không biếnreview thànhtrainingdata.
- [x] 80Python tests (labels/robustness/audio/CTC/data pipeline) +Go vet/test/build +CMS tsc/Vite +Client tsc/Next PASS.8protected hashes/review snapshot/frozen ASRmanifest/vocab unchanged. Convention `asr-label-v1-lossless` ghi ởdataset spec và `docs/T1.4_asr_label_contract.md`; evidence `data/manifests/asr_label_preflight.json` vàD:/data_training_ai/asr_label_preflight_20261020/preflight.json.

Changed:shared encoder/dataset/callers/tests +label convention/report/progress. Verified:80tests/actualpreflight/protected hashes/builds PASS. Contract touched:no productionAPI; ASRlabel convention documented. Next safe task:targeted human/audio-backed supervised examples và approvedreference evaluation trước boundedASRexperiment. Chưa retrain/deploy/repackKaggle/liveHTTP/GPU/đoWERmới; existing modelquality chưa thay đổi.

## Lịch sử — receive review JSON and diagnose errors

Task hiện tại: **DONE — REVIEW JSON RECEIVED / ERROR AUDIT; NOT TRAINING READY**. User đã điền trang rà soát và báo lỗi tiếng Anh, số liệu, trích dẫn văn bản, địa danh, từ ghép. Đã lấy file xuất thật `C:/Users/PC/Downloads/reviewed_whisper_domain_v1.json`; lưu nguyên byte tại `D:/data_training_ai/minigpt_domain_v1_20261019/whisper_review_v1/received_860f8068d0bd/reviewed_whisper_domain_v1.json`, SHA860f8068d0bd... Không đổi checkbox/origin/feedback hay train.

- [x] Đọc actual export:40transcripts,39edited,37summaries,33feedback,0verified; giữ nguyên trạng thái user gửi.
- [x] Copy SHA/73967bytes identical;40unique IDs/source-draft binding/80media hashes/8protected files PASS.31summary bằng transcript,25over95BPE+EOS,16incomplete ending,3blank; không tínhWER/CER từpartial edits.33feedback preserved,0verified giữ nguyên, không phủ nhận lượt rà lỗi user đã hoàn tất.
- [x] Active ASR93symbols thiếuF/J/W/Z,9digits vàpunctuation; actual CharVocab.encode drops unknown: FTA→TA,WTO→TO,2020→empty,9.4%→4. Candidate133 giữ được các chuỗi này nhưng chưa được promote; không suy charset coverage thành acoustic accuracy. Trang đã chấm làWhisper-base Transcribe, không phải đo pairedprojectASR hay tính năngdịch.
- [x] Report `docs/T1.6_whisper_review_intake.md`, audit trênD: và `data/manifests/minigpt_whisper_review_intake.json`; trạng thái nhận file cập nhật. Không đổi app code/API/weights/test; data-only audit assertions PASS, không rerun app builds.

Changed:reviewJSON snapshot+audit/report/progress. Verified:hashes/IDs/BPE/vocab encoder checks. Contract touched:no. Next safe task:sửa silent unknown-character handling và chốt label conventions ASR; sau đó targeted supervised data/paired evaluation, chuẩn hóa summary trước MiniGPT training. Không tự bắt đầu training.

## Lịch sử — review preprocessing

Task hiện tại: **PREPROCESSING DONE — HUMAN REVIEW / SUMMARIES PENDING** (2026-10-20). User yêu cầu bước tiếp theo sau40WhisperWeb drafts. Đã chuẩn bị rà soát có sẵn transcript và timing proposals riêng; chưa hiệu đính nội dung vì không có công cụ nghe trực tiếp, không tự xác nhận đã nghe, không tự sinh summary hay train.

- [x] Đọc startup/AI plan, draft manifest, annotation renderer/export và importer; Docker engine hiện không kết nối được. Toolset không có khả năng nghe/transcribe audio trực tiếp cho bước kiểm chứng người.
- [x] Trang http://127.0.0.1:8890/whisper_review_v1/index.html:40transcript Whisper prefilled,40summary trống,0confirmation,22flagged-first; nguồn máy được giữ và storagekey tách khỏi trang human cũ.21timing proposals/20clip,40SRT riêng, text raw giữ nguyên/alignment chưa xác minh. Không overwrite120raw exports/7prep files/8protected data+weights.
- [x] 27unit tests +Playwright desktop/mobile40cards/8playbacks/export/provenance/missing-field guard/edit clears confirmation/empty-field autosave/nooverflow +visual QC PASS. Go vet/test/build,CMS tsc/Vite,Client tsc/Next PASS. Report `docs/T1.6_whisper_review.md`, manifest `data/manifests/minigpt_whisper_review.json` cập nhật; no API change.
- [ ] Người rà soát nghe sửa40transcript, viết summary và xuất `reviewed_whisper_domain_v1.json`; sau đó intake riêng giữ origin máy hỗ trợ. Human-only importer hiện chưa nhận protocol này, không giả human-written để bypass. Chưa human semantic review/WER/CER/train/deploy; fullT1.6 vẫn chưa đạt.

Changed:review preprocessing+page+checks/docs. Verified:27tests/browser/integrity/builds PASS. Contract touched:no. Next safe task:nhận nội dung rà soát thật và summary; phần manual đang pending, chỉ phần preprocessing đã xong.

## Lịch sử — WhisperWeb conversion

Task hiện tại: **DONE CONVERSION — WHISPERWEB 40/40; HUMAN REVIEW REQUIRED** — user đổi công cụ sang https://whisperweb.dev/video-to-text?utm_source=chatgpt.com. Đã dùng free local processing trên40clip mới, tiếng Việt; giữ external-ASR draft provenance, không đổi thành human labels hoặc tự train.

- [x] Đọc trang chính thức, mở UI thực tế bằng Playwright đã cài; integrated browser vẫn lỗi kernel-assets. UI free mode hiển thị200MB/20min mỗi file, TXT/SRT/VTT/JSON.
- [x] Clip đầu đã xuất TXT/JSON/SRT thật: whisper-base291MB, Multilingual, Vietnamese, Transcribe, không quantized. Output có lỗi từ/lặp, JSON có null end và SRT fallback; giữ nguyên raw và gắn review flags.
- [x] Xử lý tuần tự40/40clip, xuất120file TXT/JSON/SRT (95244bytes), giữ30train/10val; `drafts.json` và manifest riêng trong `D:/data_training_ai/minigpt_domain_v1_20261019/whisperweb_drafts_v1`. Không cần login/payment; không bypass. Clideo đã superseded theo user.
- [x] Export integrity PASS:40ID/TXT-JSON comparisons/120output hashes/80clip media hashes/7prep packet hashes/8protected data+active weights.22clip có flag cần rà soát:6unknown end,5repeated8word,14outside30s (overlap), maxend32.34s;0exact duplicate transcripts. Không coi mechanical checks là accuracy/human verification.
- [x] Collector syntax/self-check +Go vet/test/build +CMS tsc/Vite +Client tsc/Next PASS. Report `docs/T1.6_whisperweb_drafts.md`, manifests `data/manifests/minigpt_whisperweb_drafts.json` và `minigpt_whisperweb_verification.json` cập nhật. Không train/deploy/đổi API/human labels/weights/frozen test; chưa semantic audit/WER/CER.

Changed: WhisperWeb drafts và metadata/collector/report/progress. Verified:40conversions/120exports +hashes/checks PASS. Contract touched:no. Next safe task:nghe sửa transcript và viết summary có provenance, rồi intake riêng; training_ready=false, fullT1.6 quality gate chưa đạt.

## Lịch sử — Clideo (SUPERSEDED BY USER)

Task cũ: **SUPERSEDED BY USER — 0/40 CLIDEO TRANSCRIPTS** — user yêu cầu chuyển sang WhisperWeb. Lần thử Clideo dừng tại login; không tiếp tục chờ đăng nhập Clideo.

- [x] Đọc trang chính thức: TXT/SRT export, speech-to-text cần đăng nhập; integrated browser/node tools lỗi kernel-assets. Đã truy cập trang bằng Playwright của dự án.
- [x] Upload clip30s `dom_wzKzkenrYew_1`, chọn Tiếng Việt, bấm Bắt đầu Chép lời: Clideo hiện Đăng nhập để tiếp tục. Đã mở Chromium riêng có giao diện cho user đăng nhập; chưa có transcript, chưa kiểm tra export/quota sau đăng nhập.
- [x] Kiểm tra SHA của40clip nguồn, tạo manifest công việc riêng và lưu screenshot login_required.png trong `D:/data_training_ai/minigpt_domain_v1_20261019/clideo_drafts_v1`. Không sửa labels/weights/frozen test. Chi tiết `data/manifests/minigpt_clideo_drafts.json`.
- [ ] Nếu có output, lưu Clideo draft TXT/SRT+metadata/hashes tách biệt; giữ human labels/gate/weights/test nguyên trạng. Nếu login/quota chặn, lưu evidence và nêu thao tác user cần làm.

## Lịch sử — domain label intake

Task hiện tại: **AWAITING COMPLETED LABEL EXPORT**. User báo đã kiểm chứng và yêu cầu tiếp tục; chưa tìm thấy JSON chứa transcript/summary đã điền. Không suy xác nhận qua chat thành nội dung nhãn hoặc tự gán40verified.

- [x] Kiểm tra thư mục dữ liệu/Downloads known-folder/project/data/Documents/Desktop/OneDrive theo tên nhãn, chưa thấy completed export hoặc accepted domain dataset.
- [x] Actualblank gate từ chối đúng: missing human annotator; stored labels_blank.json vẫn40transcript/summary trống. Samples/frozen files/active weights hashes unchanged.
- [x] Thử đọc browser draft qua công cụ browser/native; cả hai lỗi môi trường “failed to write kernel assets … os error3”. Không kết luận browserdraft trống; không sửa localStorage/human work.
- [ ] Nhận đường dẫn JSON đã xuất (hoặc user xuất bản nháp đang lưu ởtrang8890), rồi chạy import labels/semantic checks trước domain training.

No training/deployment started. Chi tiết @data/manifests/minigpt_domain_label_intake.json. Đây là thiếu nội dung nhãn/file, không phải yêu cầu xác nhận quyền lặp lại.

## Lịch sử — real-domain annotation preparation

# TodoWrite — T1.6 real-domain annotation data

Task hiện tại: **DONE PREPARATION — HUMAN LABELS0/40 / NOT TRAINING READY (2026-10-19)**. Đã tải nguồn mới, cắt clip và tạo paired own-ASR inputs cùng gói gán nhãn. Không bịa transcript/summary người, không train/deploy/đổi test hoặc weights.

- [x] Startup/AI skill/MiniGPT spec/plan/pilot đọc; branch phase1-ai-core; Docker engine off. Giữ48News confirmation và original test/ratings.
- [x] 20new CC sources/4new channels,499544485bytes originals trênD:. Loại toàn bộ10frozen videos/6channels, log2public403+1durationreject;5eligible/channel seededIDhash. Split channel-disjoint15train videos/5val videos,40clips×30s=20min,30train/10val. Known speakers chưa xác minh; không claim near-duplicate independence.
- [x] WAVmono16k/30s +MP4/raw source hashes/timestamps PASS.80own-ASR inputs active/candidate, CPUFP32/37.531s,0empty/0overbudget/max229prompt tokens≤416. ASR chỉ noisyinput, không humanreference/target; không MiniGPT/Whisper/external model labeling.
- [x] D:/data_training_ai/minigpt_domain_v1_20261019 córaw/sources/selection/media/samples/blanklabels/index.html/README; trang http://127.0.0.1:8890/index.html. Human fields trống/unchecked, autorestore theo packetSHA, xuấtJSON. Gate labels đúngID/hash/attestation/source-budget/complete-target/disjoint-groups, no truncate/drop; actualblankimport rejected/noacceptedexport.
- [x] 20unit tests PASS; Playwright desktop/mobile40blank cards/40videos/4representative playback mỗi viewport/decodedframe/JSON export/Unicode autosave/no overflow+visualQC PASS. Testfixtures riêngqa, không humanlabels.
- [x] Go vet/test/build +CMS tsc/Vite +Client tsc/Next14/14 PASS. Full media/source/packet/frozen model/ref/ratings hashes PASS; report/manifest/taskstatus updated. Chưa humanlabels/training/Kaggleupload/deploy/liveHTTPapp/GPUcheck; human1.6/5 unchanged.

Changed: real-domain media/ownASR preparation +annotation UI/import gate/tests/browsercheck, dataset onD:, report/manifests/progress.
Verified:20sources/40clips/80ASR inputs/hash/profile checks +20tests/browser/QC +Go/CMS/Client PASS.
Contract touched:no; no production or frozen evaluation change.
Next safe task: người nghe tự viết40transcript-summary pairs trong tranggánnhãn, xuấtJSON rồi import/audit trước bounded-domain training. Đây là nhãn mới cần viết, không lặp48News confirmation; không dùng model outputs làm target.

## Lịch sử — mixed candidate real-video pilot

Task hiện tại: **DONE — PAIRED PILOT VERIFIED / REAL-INPUT ERRORS / NOT DEPLOYED (2026-10-19)**. User “tiếp tục task”: đã chạy mixed300 vs active trên3video đã xem, giữ input cố định, production helper trong process riêng. Không train/tune/deploy/tự gán điểm human. FullT1.6 human gate vẫn chưa đạt; shared1.6/5 không đổi.

- [x] Chọn đúng candidateSHA70ec4790... từ guard-selected300, giữ activecf9cfa....
- [x] 3clips ×3input (confirmed draft/activeASR/candidateASR) ×2MiniGPT =18fresh nonempty outputs; CPUFP32/Torch2.13/temp0/max96. Active cache parity9/9. Exact prior source/service/weights/frozen samples/references/ratings/media hashes unchanged. Không chạy ASR mới.
- [x] Candidate vẫn lặp/sai: draft01 lặp Campuchia, draft10 đúng chủ đề hơn, draft28 saiNewton; hai nhánh ASR còn lệch chủ đề/lặp. Đây là qualitative diagnostic, không tự tínhaccuracy/điểmhuman hay nhận là độc lập30video.
- [x] Packet D:/data_training_ai/minigpt_news/mixed_replay_video_pilot_3_v1 cócomparison.json/review.txt/review.html/3video. Render escaping test PASS; Playwright desktop1440/mobile390,3video playback×2viewports/9pairs/no overflow +visual QC PASS.
- [x] Go vet/test/build + CMS tsc/Vite + Client tsc/Next14/14 PASS. Report/manifest/taskstatus cập nhật; Docker engine off, chưaliveHTTP/GPU, lint không chạy. Serving weights/API giữ nguyên.

Changed: isolated real-video pilot runner/review/test/browser check +packet/report/progress.
Verified:18generations/9cache parity/source+media+model hashes, render test/browser/QC +Go/CMS/Client PASS.
Contract touched:no; no deployment/training/frozen ratings change.
Next safe task:T1.6 riêng bộtrain/validation transcript thật→summary người viết từvideo mới ngoài30frozen/3diagnostic; giữ pairedownASR vàsplit/provenance. Không lặp48News audit hoặc nới guard; chưa chạy training mới.

## Lịch sử — mixed clean/ASR replay

Task hiện tại: **DONE — TRAIN/EVAL VERIFIED; SUMMARY GUARD PASS / NOT DEPLOYED (2026-10-19)**. Kaggle version1 COMPLETE; candidate mixed step300 là round duy nhất đạt guard, giữ production weights/API và frozen evaluation. Full T1.6 vẫn chưa đạt human quality gate; historical shared mean1.6/5 không đổi.

- [x] Đọc startup/AI skill/MiniGPT plan/spec/callers, branch phase1-ai-core. Docker engine không khả dụng.
- [x] Opt-in mixed replay1:1 trong mỗi microbatch (4clean+4noisy), effective64,300updates/eval60; guard clean/noisy ROUGE/EOS/repetition/cap so same-GPU init. Không export serving candidate nếu mọi round bị loại; legacy recipe vẫn tái lập được.
- [x] 62Python tests PASS, bao gồm balance/seed/coverage/hidden regression/nonfinite/no-export. 7648 encoded examples/956balanced microbatches verified;113own source/config files. Giữ nguyên956train/64val/48confirmed pair hashes/init.11prior Kaggle kernels COMPLETE trước khi submit.
- [x] Private dataset minigpt-mixed-replay-v1 READY; private kernel ai-core-minigpt-replay-v1 version1 COMPLETE.4remote sanity PASS, đủ300updates/5valrounds, output/config/checkpoint/rawpred means/IDs/hashes/guard/runtime verified. Reader giải mã log JSON đã sửa và chạy verify thật PASS, không train lại.
- [x] Selected mixed300: clean ROUGE-L0.292511→0.475816, noisy0.172177→0.186158. ASR repetition0.174653→0.162928, cap/EOS không kém init. Step240 mean cao hơn nhưng bị guard loại vì ASR repetition. Title RL0.356232→0.343602 vẫn giảm; không claim mọi tính năng cải thiện.
- [x] T4 runtime baseline+train/val446.03s, trainloss0.228532; peak allocated1.056/reserved1.805GiB≤8. Không chứng nhận six-model inference4GiB. CandidateSHA70ec4790... tách riêng, activecf9cfa... unchanged; không deploy.
- [x] Go vet/test/build, CMS tsc/Vite, Client tsc/Next14/14 PASS. PNG/SVG curves21loss+5valpoints visual QC PASS; metrics/report/manifests/taskstatus cập nhật. Chưa liveHTTP/E2E, lint hoặc real-video/human evaluation mới.

Changed: opt-in replay sampler/guard/selection +tests, private wrapper/collector/plotter, checkpoint/metrics/curves/report/progress.
Verified:62Python tests+4remote sanity; data/checkpoint/guard/config/rawmetrics/hashes +Go/CMS/Client PASS.
Contract touched:no; production weights/API/frozen ratings/references unchanged.
Next safe task:T1.6 isolated candidate vs active on real-ASR video, tách3clips đã xem thành diagnostic; fresh human ratings trên30frozen outputs trước promotion, không dùng để tune/chọn checkpoint. 48pair confirmation còn hiệu lực nếu hashes không đổi.

## Lịch sử — aligned candidate training

Task hiện tại: **DONE — TRAIN/EVAL VERIFIED; ASR REGRESSION / NOT DEPLOYED (2026-10-19)**. Xác nhận48cặp v2 qua chat đã được ghi đúng ID/hash. Kaggle version1 COMPLETE, output tải về và kiểm chứng. Full T1.6 vẫn chưa đạt; historical human mean1.6/5 không đổi.

- [x] Đọc instructions/AI skill/MiniGPT spec/pipeline; lưu rawconfirmation và provenance48ID+pairSHA, không bịa tên/người chấm/điểm chất lượng. CSV cũ backedup; split/target hashes unchanged, data gate PASS.
- [x] Private dataset traininghighlight/minigpt-aligned-summary-v2 READY; kernel traininghighlight/ai-core-minigpt-aligned-v2 version1 COMPLETE. Seed1337,956train/64val,240clean+60ASR, eval60;4remote sanity checks PASS. Historical jobs unchanged.
- [x] Tải output D:/data_training_ai/minigpt_news/aligned_output_v1; verify checkpoint/config/split/init/audit hashes,5validation rounds/selection/runtime PASS. Chọn clean180 bằng paired mean định trước; activeweights/API không đổi, không deploy/test tuning.
- [x] Same-GPU clean RL0.292511→0.517913; noisy RL0.172177→0.114637, repetition0.174653→0.328048, cap hits0.171875→0.515625. Mean tăng không đủ cho quality PASS. T4 peak allocated1.055/reserved2.520GiB; không chứng nhận six-model inference4GiB.
- [x] Post-selection3draft+3storedASR→6nonempty outputs, hashes protected. Clean outputs có cải thiện theo chủ đề nhưng vẫn lặp; ASR outputs còn sai/lặp. Không tự chấm human score hoặc dùng control chọn checkpoint.
- [x] 50Python tests+4subtests, Go vet/test/build, CMS tsc/Vite, Client tsc/Next14/14 PASS. Báo cáo/metrics/curves PNG+SVG+data/manifests cập nhật. Docker engine off, chưa liveHTTP/E2E/GPU local; lint chưa chạy.

Changed: candidate training/collection scripts, user confirmation record, metrics/curves/video control/report/task manifests.
Verified: output/config/checkpoint/hash/selection +4remote sanity +50local tests/4subtests +Go/CMS/Client PASS.
Contract touched: no; production weights and frozen ratings/references unchanged.
Next safe task: T1.6 mixed clean+ASR replay trong batch và guard không giảm từng điều kiện; dùng lại48cặp đã xác nhận nếu hash không đổi, không yêu cầu audit lại. Chưa chạy thí nghiệm mới.

## Lịch sử — label-audit preflight

Task hiện tại: **TECHNICAL PREFLIGHT + DATA V2 DONE — HUMAN AUDIT PENDING (2026-10-19)** — phát hiện/sửa guard chấp nhận teaserellipsis; v2 có956train/64val,48humanrows vẫn0reviewer/0verdict. Chưa train candidate hoặc tự gán xác nhận của người; fullT1.6 vẫn FAIL.

- [x] Đọc instructions/AI skill/spec MiniGPT/recipe; branchphase1-ai-core, Docker engine vẫn không khả dụng; kiểm tra CSV48/48còntrống.
- [x] 4sanity CPU PASS: gradient<1e-4, AdamW<1e-6, BPE10000/10000, toyMiniGPTd64/L2 overfit300steps loss≈0.0002 +generate. Không phải train full14Mcandidate; activeSHA cf9cfa... giữ nguyên.
- [x] V1 guard lỗi:50train+3val có ending../.../…; đã thêm has_sentence_ending shared filter+trainer refusal, regressiontests41+4subtests PASS. Mechanical source spans/fullsource48cases lưu riêng, semanticNOTADJUDICATED, không ghi reviewer/verdict. Body/summary/title exact-normalized duplicates0 trong/crosssplits; không near-duplicate guarantee.
- [x] Rebuild V2 D:/data_training_ai/minigpt_news/aligned_summary_v2_20261019:956/64, excludeall53, preserve oldsplits/61valIDs+3replacement; reserve201644rows. 8160item checks/4productionparity PASS; unchangedcheckpoint cleanRL0.294504 vsLead0.415168, syntheticASR0.173516 vs0.114252, mean0.234010; datachanged≠modelimproved. Schedule240/60/eval60. V1files/hashes retained +additiveSUPERSEDEDnotice, v1manifest snapshot saved.
- [x] Go vet/test/build, CMS tsc/Vite, Client tsc/Next14/14 PASS. V2bundle13files/codezip/owninitcopy/hashes +README verified; report @docs/T1.6_label_preflight.md, manifests @data/manifests/minigpt_label_preflight.json +minigpt_aligned_summary.json. No candidate job/upload/deploy/testsettuning. Docker engine unavailable; noHTTP/GPUcheck.

Changed: ending guard/rootfilter +tests, mechanical audit evidence, candidate data/bundlev2 and progress.
Verified:41tests/4subtests+4sanityitems+8160encodedchecks+4productionparity+Go/CMS/Client PASS.
Contract touched:no; actualproductionmodel/API/frozenratingsrefs unchanged.
Next safe task: cần người xác nhận48cặp trong v2/human_audit.txt và CSV (hoặc cung cấp fileđãràsoát đúngID+pairSHA), resolve rejects/newversion+refresh provenance rồi candidate GPU train. Tự động chỉ kiểm tra cấu trúc/nguồnkhớp, không được tự nhận là human review.

## Lịch sử — aligned summary data + validation selection

Task hiện tại: **PREPARATION DONE — HUMAN LABEL AUDIT PENDING (2026-10-19)** — đã chuẩn bị984train/64val editorial pairs, sửa sum-based selection và kiểm tra checkpoint thật. Không train/deploy; không dùng video frozen/draft làm nhãn. FullT1.6 vẫn FAIL.

- [x] Đọc instructions/AI skill/spec MiniGPT + callers train/eval; giữ legacy headline experiment và production API.
- [x] Screen76000/4000→391/24; bổ sung từ197135rawrows của pinned train shard→+593/+40. Final984/64, preserve originalsplits, reserve95/5hash, exclude1000frozenIDs (IDfield only, không dùng score/reference để chọn); không hạ filter. Có reasons/hash/provenance và48auditrows còn trống.
- [x] Manifest sum-aligned-v1: cùng body/source_asr cho3formats, no source/label truncation, source edges strip nhưproduction. Chọn mean sumRL clean+noisy trêncùng64IDs; title/cap regression riêng. Schedule4clean+1ASRpasses=248/62steps, eval62; legacy16000/4000 giữ nguyên. Trainer chặn pending/rejected audit/thiếu64val; không tự mở frozen test.
- [x] 8384encoded item checks+4realproduction parity PASS; baseline unchanged weights: cleanRL0.290132 vsLead0.407114, syntheticASRRL0.175906 vsLead0.115482, selection0.233019; không qualitypass/globalaccuracy. 31tests+4subtests; Go vet/test/build +CMS tsc/Vite +Client tsc/Next14/14 PASS. Packet/codezip/initcopy/checksums verified, chưa upload/submitKaggle. @docs/T1.6_aligned_summary_preparation.md; @data/manifests/minigpt_aligned_summary.json.

Changed: screened editorial candidate dataset +opt-in sum recipe/epoch budget +audit packet/bundle/report/progress.
Verified:31Python tests/4subtests,8384item checks,4production parity, Go/CMS/Client PASS; activeMiniGPT SHA cf9cfa... giữ nguyên.
Contract touched:no; không đổi production/API/weights/frozen ratings.
Next safe task: người đọc48cặp trong human_audit.txt và ghi reviewer/verdict vào human_audit.csv; resolve rejects/reversion+refresh provenance trước candidate GPU train. Đây là kiểm chứng nhãn, không phải điểmhuman1–5 mới. Dữ liệu vẫnNews+syntheticnoise, chưa có bộhuman transcript→summary khácdomain.

## Lịch sử — T1.6 MiniGPT prompt/chunk/target diagnostic

Task hiện tại: **DIAGNOSTIC DONE (2026-10-19)** — đã kiểm tra prompt/EOS/mask/KVcache, trace chia đoạn trên validation News và audit target/truncation/selection. Không đổi weights/production/contract; fullT1.6 quality gate vẫn FAIL.

- [x] Đọc train dataset/runner và production summarizer: train mix title:sum:cap2:1:1, chọn checkpoint bằng title ROUGE-L; serving mặc địnhsum và recursive map-reduce.
- [x] Prefix parity253train+8val, mask/EOS8val, real KV-cache/fullforward8steps PASS;3draft frozen chỉ222/250/271tokens<411, không mapreduce. Không thấy lỗi kỹ thuật trong phạm vi kiểm tra; không quy mọi lỗi choASR/chunking.
- [x] Đếm76000train/75581sum, không trùng4000val; audit253eligible từ256train đầu:144source/11target bị cắt,46publisher-style prefix. Fixedval129–136:16calls,3longinputs rawtoken coverage PASS; ROUGE-Lsum0.174967 vsLead0.209702 trên8mẫu, không globalclaim/testtuning. Một finalreduce lặp94.68%trigram; đầu vào ngắn vẫn đổi ngày/số/entity.
- [x] @docs/T1.6_pipeline_diagnostic.md +rawpacket D:/data_training_ai/minigpt_news/pipeline_diagnostic_20261019/diagnostic.json +manifest. 16tests/4subtests PASS; Go vet/test/build, CMS tsc/Vite, Client tsc/Next14/14 PASS. Docker engine off nên không liveE2E/GPUcheck. Recipe next: grounded human targets/complete labels, sum-based validation selection, separate long-input quality; chưa tự train/deploy.

Changed: diagnostic runner/tests, report/manifest/progress; không sửa production.
Verified: exact checkpoint checks+16Python tests/4subtests+Go/CMS/Client PASS.
Contract touched: no.
Next safe task: T1.6 chuẩn bị dữ liệu/recipe transcript→summary có nhãn người, selection theo sum; giữ30cliptest và3draft ngoài train.

## Lịch sử — candidate ASR real-video pilot

Task hiện tại: **PAIRED PILOT + USER FEEDBACK + DIRECT-DRAFT CONTROL DONE (2026-10-19)** — đã chạy sample_01/10/28×ASR cũ/candidate→cùngMiniGPT, ghi nhận user xác nhận nội dung3draft và đánh giá candidate summaries1/3sai,2đúng. Đã chạy thêm chính3draft→cùngMiniGPT; vẫn thấy lỗi/lặp. Không deploy/đổi frozen test hoặc tự gán điểm human.

- [x] Đọc pipeline service và packet frozen; Docker engine không khả dụng, root .venv có đủ dependency để chạy trực tiếp hàm production trong tiến trình CPU riêng.
- [x] Đủ6ASR+6summary nonempty, cùngMiniGPT SHA/profile;3baseline ASR khớp frozen outputs chính xác. Segment≤60s, media/model/ref/ratings hashes giữ nguyên. Packet `D:/data_training_ai/minigpt_real_video_20261015/asr_candidate_comparison_3_20261019`, rawcomparison.json+3sampleJSON.
- [x] Review.html có3video,2cột ASR/summary, draft pretrained chưa kiểm chứng và3form lời chuẩn/tên/checkbox; không prefill nhãn máy. Xuất human_references_3.csv riêng, không sửa references.csv gốc. Playwright3cards/video playback/decoded frame/export gate/Unicode CSV roundtrip/desktop+mobile/no overflow+visual QC PASS; test CSV riêng dưới tools/tmp, không phải nhãn thật.
- [x] 3metric-gate/render tests PASS; Go vet/test/build, CMS tsc/Vite và Client tsc/Next FULL PASS. Report `docs/T1.4_asr_candidate_video_pilot.md` +manifest/master cập nhật. MiniGPT vẫn lặp/thêm chi tiết không hỗ trợ bởi transcript; không coi clean benchmark pass là real-video quality pass.
- [x] User xác nhận đúng nội dung3draft qua chat; card1=sample_01/card2=sample_10/card3=sample_28. User chấp nhận MiniGPT từASRmới ởcard2, không chấp nhậncard1/3; không suy từ nhận xét này thành rawASR word accuracy hoặc điểm1–5.
- [x] Direct-draft control3/3nonempty, cùngMiniGPT/profile/temp0/max96; mẫu10lặp “an ninh”, mẫu28lệch nội dung tiểu sửNewton. Rawfeedback/control JSON+confirmed_draft_review.html và @docs/T1.6_confirmed_draft_diagnostic.md. Reference/ratings/frozen outputs/weights gốc giữ nguyên.
- [ ] CER/WER theo reference đã đối chiếu từng từ và điểm human1–5 mới chưa có; xác nhận nội dung3draft đã được ghi nhận, CSV gốc vẫn0/30. FullT1.6 chưa đạt; ưu tiên chẩn đoán/improve MiniGPT với train/validation khác, không train3cliptest.

## Lịch sử — ASR fine-tune có nhãn người tạo

Task hiện tại: **TRAIN/EVAL DONE — VIDEO VALIDATION PENDING (xác nhận2026-10-19)** — Kaggle COMPLETE,4000steps/best3500, output đã tải và kiểm chứng. User ưu tiên ASR, giữ nguyên MiniGPT; không dùng3draft Whisper/30video frozen làm nhãn train hoặc tự nhận human references. Candidate chưa deploy.

- [x] Checkpoint active ASR d256/8layers/8heads/n_chars93/best20000 và MiniGPT giữ nguyên SHA. Runtime kiểm tra2026-10-19: Docker Desktop engine không khả dụng; chưa khởi động stack hoặc test serving trong task kiểm tra Kaggle.
- [x] Đã kiểm tra references.csv ngày19/10:0/30reference được điền; chưa nhận nhãn đã xác nhận để đo CER/WER video.
- [ ] Nhận3draft đã được người nghe kiểm chứng/sửa thành human references, rồi đánh giá candidate trên real-video với MiniGPT giữ nguyên; không dùng draft máy làm ground truth.
- [x] Audit FLEURS vi_vn revision168de341b3db6859a9bac1c50a2ef5e3b47647e0, CC-BY-4.0; human translation/read/validation theo paper. Raw3parquet trênD:, giữ VIVOS speaker split và FLEURS official splits; IDs/audio fingerprints không giao nhau. Train VIVOS10567+FLEURS2994≈22.0102h, dưới mục tiêu30h.
- [x] Recipe candidate: encoder/loss giữ nguyên; head/vocab93→133 chỉ thêm train chars, prefix93 giữ nguyên. Loại4train CTC-infeasible có log, giữ đủval/test; còn13557train≈22.0073h. Seed1337/4000steps/batch4×accum4/lr1e-4/balanced domains/speed+gain+noise+SpecAugment. Chọn fullvalidation mỗi500steps, test cuối cùng; best ban đầu được bảo vệ, không auto-deploy.
- [x] 21focused Python tests PASS; real checkpoint head expansion/train count PASS; activeASR/MiniGPT hashes giữ nguyên. Go vet/test/build +CMS tsc/Vite +Client tsc/Next FULL PASS. 104Python files đóng gói/hash, không kèmAPIkeys/pretrained assets.
- [x] Upload private human dataset≈699MB; private kernel `traininghighlight/ai-core-asr-robust` v2 COMPLETE, API xác nhận lại2026-10-19 không failure. v1 lỗi auto-extract lồng thư mục trước training đã sửa+2tests; v2 TeslaT4/FP16 chạy thành công.
- [x] Persisted execution log xác nhận4sanity lines PASS và optimizer step1→4000; best3500 do validation chọn, loss cuối0.49316; train+finaleval4457.07s. Snapshot `data/manifests/asr_robust_training.json` đã cập nhật.
- [x] GPU candidate đã train/evaluate; output/checksum/fulltest counts verified tại `D:/data_training_ai/asr_robust/outputs-v2`, report `docs/T1.4_asr_robust_metrics.json`. Validation recommendation=True; VIVOS threshold pass=True. Chưa deploy/chưa có video human references.
- [x] Bộ thu output đã hoàn tất15/10≈15:38ICT; không còn chờ training. Ngày19/10 verify lại checkpoint/config/prefix93IDs/4exclusions/traincounts/test macro+corpus arithmetic/raw-repo report parity. Best SHA d03ef0a962220618e90e5ff478a2fbab5ff35dd68deb539a4933eb7c15a4f3de. VIVOS testWER36.0519→32.9727%/CER13.5446→12.4467%; FLEURS WER76.7465→53.6727%/CER50.5133→23.9063%. VRAMtrain allocated1.203/reserved3.039GiB; không chứng nhận inference4GiB. Không deploy.
- [x] Recheck19/10:10candidate/wrapper tests, Go vet/test/build, CMS tsc/Vite, Client tsc/Next FULL PASS;4000TensorBoard loss points+9validation points render PNG/SVG và visual QC PASS. Todo/master/report/trainingmanifest cập nhật kết quả thật, API contract giữ nguyên.

Chi tiết: `docs/T1.4_asr_robust_training.md`; input manifest `data/manifests/asr_robust_dataset.json`; raw output trênD: giữ nguyên. Còn lại: human references0/30 và controlled real-video ASR→MiniGPT evaluation; chỉ1seed/~22h train, FLEURS WER53.67% vẫn cao. T1.6 human quality chưa được đánh giá lại.

## Lịch sử — ASR pretrained draft3mẫu (ngoại lệ user cho phép)

Task đã thực hiện: **DONE TECHNICAL — 3 PRETRAINED DRAFTS READY / HUMAN VERIFICATION PENDING (2026-10-15)**. User đã cho phép rõ ràng ngoại lệ ASR pretrained cục bộ, chỉ tạo bản nháp `sample_01`/`sample_10`/`sample_28`, lưu riêng trên D:. Không hỏi lại cùng quyền này; ngoại lệ không mở rộng sang training/ground truth hoặc thay6model dự án.

- [x] Đọc nguồn chính faster-whisper/CTranslate2 CPU int8; kiểm tra audio3mẫu và tài nguyên. C: ít chỗ nên environment/cache/model/temp đều đặt trên D:.
- [x] Environment `D:/data_training_ai/tools/asr-draft-venv`, faster-whisper1.2.1/CT2 4.8.3/PyAV18.1; model multilingual small revision536b0662742c02347bc0e980a01041f333bce120, model SHA3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671. Medium load thiếu bộ nhớ; small CPU INT8 chạy thành công, không cầnAPIkey.
- [x] Đủ3WAV×60s→3TXT/3SRT/3JSON +drafts.csv/review.html/manifest/README tại `D:/data_training_ai/minigpt_real_video_20261015/pretrained_drafts_3/`;33segments,979/1037/1095ký tự, ASR62.062s. Tất cả PRETRAINED_DRAFT_UNVERIFIED/human_verified=false.
- [x] MiniGPT từ3draft vẫn có lỗi: sample10lặp an ninh, sample28bịa người đàn ông/bệnh tật; case1thêm ngữ cảnh kiểu báo. Chỉ diagnostic nhãn máy, không chính thức CER/WER hoặc đánh giá factual truth của draft.
- [x] 5export/timestamp/scope tests PASS, Go vet/test/build, CMS tsc/Vite, Client tsc/Next FULL PASS. SRT giới hạn end≤60s, raw JSON giữ thời gian model. Reports/manifests/master cập nhật; reference/checkpoints/raw outputs/ratings không sửa.
- [x] Final QC:3drafts/33segments/TXT/SRT/CSV/JSON hashes và timestamps≤60s PASS; browser3cards/3video controls/3comparison panels +actual video playback PASS; reference/ratings/frozen30/checkpoint hashes giữ nguyên, inference6real/no degraded healthy.
- [ ] Còn lại: người nghe kiểm chứng/sửa3draft rồi mới điền reference/transcriber và đo CER/WER video. Không mở rộng sang30mẫu hoặc training theo ngoại lệ chỉ3draft.

Changed:3pretrained drafts và paired diagnostic, environment/model tách biệt trênD:, source/version/hash và báo cáo.
Verified:3nonempty drafts/33segments/SRT bounded/source hashes;5tests +Go/CMS/Client FULL PASS.
Contract touched: no.
Next safe task: kiểm chứng3draft thành human references, tách lỗi ASR/MiniGPT trước training trên nguồn khác; fullT1.6 vẫn NOT MET.

## Lịch sử — T1.4/T1.6 Chẩn đoán ASR→MiniGPT, bước3

Task hiện tại: **PARTIAL — DIAGNOSTIC DONE / VIDEO TRANSCRIPTION PENDING (2026-10-15)**. Chẩn đoán ASR train/inference và MiniGPT với reference đúng hoàn tất; chưa thể chép lời chuẩn30clip do thiếu công cụ nghe/nhãn người tạo, không tạo pseudo-label làm reference.

- [x] Xác nhận runtime Up/healthy,30reference hiện trống; tool hiện có không cung cấp khả năng nghe audio trực tiếp cho agent.
- [x] Đọc ASRDataset, log-Mel, service/chunk/decode, notebook train; cùng feature log-Mel80/FFT400/hop160/16kHz, không thấy bước CMVN khác giữa hai đường trong source đã đọc.
- [x] VIVOS30pilot: macro WER35.3647%/CER13.9602%; corpus WER37.8641%(117/309)/CER15.5199%(203/1308), chỉ subset109.99s không phải full760câu hoặc YouTube.
- [x] Active ASR hash đúng;3utterance: dataset/service audio,mel,direct/service greedy text khớp API đã lưu;3clip60s ghép stream20s phục hồi đúng audio. Không phát hiện mismatch ở phạm vi kiểm tra này.
- [x] MiniGPT API nhận3reference VIVOS đúng vẫn bịa/lặp (case1source yêu bạn→tin Trung Quốc/nhập viện;case3lặp ông). Lỗi MiniGPT có thể xuất hiện độc lập với ASR; không coi3case là human quality score.
- [x] Kiểm tra10metadata YouTube: không có uploader subtitles, chỉ automatic_captions vi. Không lấy auto captions làm nhãn chuẩn.
- [x] Theo đề xuất FFmpeg của user: chạy ffprobe trên đủ10video gốc, tất cả chỉ có video+audio,0subtitle tracks. Audit tại `D:/data_training_ai/minigpt_real_video_20261015/asr_ground_truth_30/ffprobe_subtitle_audit.json`; không có track văn bản để FFmpeg trích xuất.30WAV mono16k đã được tách và chạy ASR thật từ trước.
- [x] `docs/T1.4_asr_diagnostic.md/.json` +D:/.../asr_ground_truth_30/diagnostic.json lưu bằng chứng;3metric tests và runtime assertions PASS. Không đổi weights/contract/train/test-selection.
- [x] Go vet/test/build, CMS tsc/Vite, Client tsc/Next full build PASS. Transcript/reference/video CER/WER chưa hoàn tất; không đánh dấu full task DONE.
- [ ] Còn lại: người nghe chép/kiểm chứng30clip, rồi đo CER/WER video và clean-transcript summary diagnostic; không train trên frozen evaluation.
- [x] Kiểm tra bước thử3mẫu theo user: `sample_01`/`sample_10`/`sample_28` thuộc3kênh, audio/video có đủ; reference và transcriber của cả3 vẫn trống. Chưa chạy metric hoặc gán nhãn cho3mẫu này; cần người nghe xác nhận lời chuẩn, không tiếp tục vòng lặp ASR tự chấm chính nó.
- [x] Thử truyền8giây audio sample_01 trực tiếp qua audio tool: hệ thống trả `audio content omitted because you do not support audio input`. Không nhận được nội dung để chép; chưa sinh transcript.
- [ ] Chờ user quyết định ngoại lệ dùng ASR pretrained cục bộ tạo draft3mẫu riêng trên D:. Skill hiện cấm model ngoài/pseudo-label; chưa cài/tải/chạy công cụ ngoài hoặc dùng draft làm ground truth/training.

## Lịch sử — T1.6 Human Evaluation (theo thứ tự đã chốt)

Task đã thực hiện: **TỔNG HỢP SHARED HUMAN SUBMISSION DONE — QUALITY BELOW THRESHOLD (2026-10-15)**. Mean1.6/5<3/5; full T1.6 NOT MET. User xác nhận3người đã chấm giống nhau, nộp một file `ratings_rater_1.csv`;30điểm nằm ở cột notes. Giữ nguyên raw submission; không nhân bản thành3phiếu độc lập.

- [x] Kiểm tra Compose: gateway8000/CMS5173/Client3000 Up, inference8001 healthy.
- [x] Kiểm tra lại frozen30 mẫu,60 media hashes,ZIP SHA/CRC và3phiếu30IDs/phiếu: đúng, không ghi đè dữ liệu/điểm.
- [x] Bộ chấm/README/rubric sẵn tại `D:/data_training_ai/minigpt_real_video_20261015/evaluation/`; ba người dùng ba CSV riêng và chấm độc lập.
- [x] **Bước1 nhận shared submission:**30điểm trong notes của file1; file2/3trống. Ghi nhận user báo3người có kết quả giống nhau; không độc lập kiểm chứng90điểm/3phiếu và không tính kappa/CI.
- [x] **Bước2 tổng hợp:**25mẫu×1,1mẫu×3,4mẫu×5; mean1.6/5,5of30mẫu≥3. Mean3người theo xác nhận đồng nhất cũng1.6; không phải accuracy của cả6model. File gốc và backupSHA `6b0e7741353624bc1d6b63966854ef244e6b7d5a17cbf2668aeb00446630f1fd` giữ nguyên; normalized riêng, không sửa file2/3.
- [x] `docs/T1.6_real_video_shared_human_results.json` +report/master/manifests cập nhật;5new+8existing tests PASS. Scorer3phiếu gốc giữ nguyên, không hạ validation để lấy PASS.
- [x] Kiểm tra phiên tổng hợp: Go vet/test/build, CMS tsc/Vite, Client tsc/Next full build và git diff --check PASS; không đổi API/weights, không commit/push.
- [x] Chuẩn bị handoff bước3: `D:/data_training_ai/minigpt_real_video_20261015/asr_ground_truth_30/references.csv`,30audio paths/IDs đúng; reference/transcriber trống0/30,README cách chép lời; không tự tạo nhãn.
- [ ] Bước3 còn lại: chép lời chuẩn và đo CER/WER để tách lỗi ASR khỏi summary. Pilot30phút thời sự/giọng kể không thay full1–2h thể thao/game OOD theo spec.
- [ ] Bước4: chỉ chốt training tiếp sau phân tích lỗi; dùng tập train/validation khác, không đưa30mẫu frozen evaluation vào train/chọn checkpoint.

Reproduce shared results: `.venv/Scripts/python.exe dist/kaggle/kernel-minigpt-news/evaluate_shared_ratings.py`.
Scorer3phiếu riêng vẫn ở `score_human_pilot.py`; chưa đủ3phiếu thì không nhận full protocol. Không cần đợi3phiếu mới để thừa nhận shared mean1.6<3 và phân tích chất lượng. Đầu vào tiếp theo là reference người chép; chưa train/đổi weights.

## Lịch sử — T1.6 Real YouTube Evaluation Corpus

Task đã thực hiện: **DONE TECHNICAL — HUMAN RATINGS PENDING (2026-10-15)**. Đã tải YouTube và giữ video gốc/provenance tại `D:/data_training_ai/minigpt_real_video_20261015`; đủ30 mẫu ASR→MiniGPT thật. Full T1.6 chưa tick vì chưa có90 điểm người.

- [x] Tải đủ10 video CC tiếng Việt/6kênh,133.36phút/513,923,365bytes; giữ original audio+video, metadata/URL/channel/license/SHA-256 trên D:.
- [x] Cố định30 đoạn60giây ở60/150/240s trước inference; selection.json khóa source hash và cả2 checkpoint hash, giữ nguyên file gốc.
- [x] Actual ASR→News MiniGPT30/30 (~44s inference CPU),0empty; review HTML/30video/30WAV/outputs nguyên văn +3CSV×30 điểm trống. ZIP151,014,531bytes trên D:.
- [x] Verify10 original SHA,60 derived media SHA,30clip/audio durations/streams,protocol non-overlap,90blankratings; ZIP SHA/CRC/file parity; browser30cards/video controls và actual H264 playback/frame decode PASS.
- [x] 8 regression checks scorer/packet PASS; Go vet/test/build, CMS tsc/Vite, Client tsc/Next FULL PASS. Reports/master/manifest cập nhật; không đổi contract/weights, không commit/push.
- [ ] **Human remaining:**3 người chấm độc lập90 điểm,mean≥3/5. Hiện0/90,mean=null. ASR video thực tế rất nhiễu; có summary lặp dài, chưa đạt/không tự gán human PASS. Giữ frozen evaluation riêng khỏi training.

Changed: nguồn YouTube thật và bộ chấm trên D:, downloader/packet/scorer +8 checks, provenance và báo cáo.
Verified:10original/30clips/30real model outputs/90blankcells/ZIP/browser playback; Go/CMS/Client FULL PASS.
Contract touched: no.
Next safe task:3 người chấm bộ video thật; phân tích lỗi ASR→summary trước khi train thích ứng trên tập training khác. T4.3 GPU vẫn chưa đo.

## Lịch sử — T1.6e News Inference Integration

Task đã thực hiện: **T1.6e — DONE LOCAL TECHNICAL (2026-10-15)**. News checkpoint đang phục vụ local Docker; **full Mini-GPT DoD HUMAN PENDING**, chưa tick toàn bộ T1.6.

- [x] Nối prompt `<sum/title/cap> source <eos>`, noBOS, metadata512/96; raw backend→sum, actual CTC ALLCAPS→lowercase; không thêm noise vào inference.
- [x] Recursive map-reduce dùng đủ source tokens, có guard không-shrink và empty-map; input không lời→empty, không fallback nội dung giả. Validate max_tokens/temperature.
- [x] Backup old wiki best/last/BPE có checksum tại `E:/checkpointhighlight/minigpt_wiki_before_news_20261015/`; copy/verify News best+BPE active, SHA256`cf9cfa7141d40f9d40b0065ae68855ff39ffe750260ee7b42c7c0eac719330ac`.
- [x] Docker Desktop/Compose start +inference rebuild/recreate; gateway8000/CMS5173/Client3000/inference8001 cùng dependencies Up/healthy,6 real models/no stub/no degraded.
- [x] HTTP/direct parity đủ3 format; raw=sum, uppercase/lowercase parity, auth401/budget422; real HTTP1120 BPE tokens (~1.81s) PASS; multilevel coverage/empty-map/reload regression PASS. Đây là test kỹ thuật, không PASS factual quality.
- [x] Python **37 PASS+1opt-in skip**, Go vet/test/build, CMS tsc/Vite, Client tsc/Next FULL, E2E types PASS. Playwright T4.1/T4.2 final **3 PASS (37.2s)**.
- [x] Bộ chấm **30 real-ASR VIVOS test utterances**, seed1337/15speakers/109.99s, audio→actual ASR→News summary qua API; audio hashes+ZIP+samples hash checked. V2 có CTC lowercase fix, v1 giữ làm lịch sử.
- [x] Packet `data/processed/minigpt_human_pilot_20261015_v2/` +ZIP: review.html,30WAV,raw/reference/ASR/summary/provenance,3CSV×30scores trống+rubric+license. Scorer guards90ratings/range/frozen samples; kết quả hiện **0/90,mean=null**, không tự chấm.
- [x] Report `docs/T1.6e_bao_cao.md`, inference/pilot JSON,checkpoint manifests/master cập nhật trạng thái local thực tế; không commit/push.
- [ ] **Human remaining:**3 người chấm độc lập90 điểm thật; cần nguồn video thực tế cho full30-summary video DoD. VIVOS chỉ pilot giọng đọc, chưa đại diện video; user chưa cung cấp path/IDs. Model vẫn có hallucination/lặp; giữ editor duyệt.
- [ ] **GPU remaining (T4.3):** CUDA VRAM/20video chưa đo; CPUhealthVRAM0 không là PASS4GB. Không bắt đầu task GPU trong phiên này.

Changed: inference prompt/profile/CTC casing/map-reduce; backup/local activation; real-ASR pilot và grading tools.
Verified: Python37+1skip, Go/CMS/Client FULL,3Playwright PASS; API/direct3format +1120token;30realASR và90 ô điểm trống.
Contract touched: no new endpoint/field/port; constraints tham số decoding nội bộ được validate.
Next safe task: lấy video tiếng Việt thực tế và3phiếu chấm độc lập; tổng hợp chất lượng trước quyết định rollout/train tiếp.

## Lịch sử — output review trước khi tích hợp

# TodoWrite — T1.6c–d Mini-GPT News Output Review

Task đọc/tải/đánh giá output: **DONE (2026-10-15)**. Training **COMPLETE**, **ROUGE-L PASS**; full Mini-GPT DoD **PARTIAL — HUMAN/INTEGRATION PENDING**, không tick toàn bộ T1.6.

- [x] Xác minh private Kaggle `traininghighlight/ai-core-minigpt-news` v2 COMPLETE; tải đủ14 file/278,563,521 bytes về `D:/data_training_ai/minigpt_news/output-v2/`.
- [x] Train clean16000 +ASR4000,3.0383h T4/fp16; selected ASR best3000 từ clean best7000, seed1337. BPE/kiến trúc/loss tự viết giữ nguyên.
- [x] Đối chiếu checksum cả3 split76k/4k/1k; ID disjoint;1000 IDs/references/reconstructed full Lead-1; recompute1000 ROUGE-L và paired bootstrap CI khớp hoàn toàn.
- [x] **Test ROUGE-L0.202308 vsLead-1 0.187109, delta+0.015199, CI95[+0.003965,+0.026687] — PASS tiêu chí tự động**. ROUGE-1 0.212911 vs0.212423; ROUGE-2 0.108957 vs0.113325. Wins/ties/losses497/39/464;226 zero-ROUGE-L;0 empty.
- [x] Strict CPU load/finite weights +full1000-example forward/PPL11.7081 (15444 target tokens);3-format generation smoke PASS kỹ thuật. Không coi smoke là PASS chất lượng: `<sum>` vẫn bịa/lặp thực thể.
- [x] Checkpoint SHA-1`656acdd50eaeacbcf45a00b02edeb77ba69447b5`, SHA-256`cf9cfa7141d40f9d40b0065ae68855ff39ffe750260ee7b42c7c0eac719330ac`; candidate/BPE/config/seed/inventory tại `data/manifests/minigpt_news_checkpoint.json`.
- [x] Kernel4 sanity PASS;20k TensorBoard loss finite. Local48 regressions PASS; Go vet/test/build, CMS tsc/Vite, Client tsc/Next FULL PASS; git diff --check PASS.
- [x] Báo cáo `docs/T1.6c_news_evaluation.md`, metrics/audit JSON và loss/val PNG+SVG; master/training report cập nhật kết quả thật, giữ lịch sử wiki FAIL.
- [ ] Full DoD: human eval30 summary từASR thật ×3 người, mean≥3/5; chưa có điểm, không suy từ ROUGE.
- [ ] T1.6e integration/deployment: `services.py:84` hiện raw prompt+BOS/chunk900 chưa khớp `<format> source <eos>`/budget512/96. Review này không đổi service/active checkpoint. Docker Linux engine không chạy nên chưa API/E2E/long-transcript/VRAM.

Đánh giá: headline metric vượt Lead-1 hẹp; ROUGE-2 thấp hơn, một số mẫu sai thực thể/chủ đề. Chỉ phù hợp gợi ý có editor kiểm duyệt; chưa chứng minh dùng tốt trên video thật. Không train mới/chọn model theo test, không deploy/commit/push.

Changed: tải đủ output; audit/plot tái lập, metrics/curves/manifests và trạng thái.
Verified: independent frozen-test1000 ROUGE-L PASS +checkpoint/CPU smoke; Python48, Go/CMS/Client FULL PASS.
Contract touched: no.
Next safe task: nối prompt/budget inference đúng format trên staging; test E2E và đánh giá real-ASR30×3 trước deployment.

## Task trước — T4.3 Inference Memory

Task đã xử lý trong phiên: **T4.3 — PARTIAL, CPU MEMORY VERIFIED / GPU VRAM NOT MEASURED (2026-10-14)**. Không tick DONE đầy đủ; chưa bắt đầu T5.1.

- [x] Compose ps: gateway/CMS/Client/inference/Milvus Up; đọc startup/backend plan/contract/registry/GPU queue.
- [x] Xác minh phần cứng: Windows chỉ Intel UHD 630; Docker --gpus all exit125 `no adapters were found`. Torch2.14.1+cpu/cuda_build=null; evidence `docs/T4.3_hardware.json`. **VRAM CUDA chưa đo, không PASS=0**.
- [x] **CPU: 2 warmup + 20/20 video thật tuần tự, 1 Playwright PASS (3,0m)**. Inference first/last median RSS 569,26→569,87MiB (+0,61), peak589,51MiB/tailrange0,17. Gateway +0,11MiB, ingest −15,25MiB. 88 stage events; không restart/GC/empty_cache. `docs/T4.3_cpu_memory_metrics.json`.
- [x] Fix GPUQueue giữ fn/fut/result cuối khi idle; regression weakref FAIL trước/PASS sau. Python **27 PASS +1 opt-in skip**, Go vet/test/build, CMS tsc/Vite, Client tsc/Next FULL lint/build, E2E types PASS.
- [x] E2E hồi quy T4.1/T4.2 **3 PASS (46,7s)**; tắt trace về0, runtime gateway/CMS/Client/inference/Milvus Up/healthy, HTTP200, live vectors vẫn18. Không publish/sửa/xóa video người dùng có sẵn.
- [ ] **GPU remaining:** build CUDA image + đo peak VRAM ≤4GiB và 20 video trên NVIDIA. Compose GPU override config PASS; execution chưa chạy do thiếu adapter.
- [x] Báo cáo/master/TodoWrite cập nhật PARTIAL theo số đo thật: `docs/T4.3_bao_cao.md`, `T4.3_hardware.json`, `T4.3_cpu_memory_metrics.json`. CUDA Compose config PASS; không tải/build CUDA image trên máy không có NVIDIA.

Changed: GPUQueue giải phóng last request/future/response; opt-in stage metrics; Playwright sampler 2 warmup +20 sequential uploads; Docker CUDA override/ARG.
Verified: CPU20/20 PASS, Python27 PASS, Go/CMS/Client FULL checks PASS, 3 E2E regression PASS; không forced GC/empty_cache/restart trong phép đo. Peak RSS inference589,51MiB; median tail growth +0,61MiB.
Contract touched: no (OpenAPI/ports giữ nguyên; trace nội bộ).
Next safe task: **hoàn tất phần GPU của T4.3 trên máy NVIDIA/CUDA**, rồi T5.1. Máy hiện chỉ Intel UHD630, Docker GPU probeexit125. Chưa commit/push; chưa test video dài/tải/GPU concurrency; CPU health VRAM0 không phải PASS4GiB.

## Task trước — T4.2 Visual Search

Task vừa hoàn thành: **T4.2 — DONE, REAL VISUAL SEARCH / LOCAL VALIDATED (2026-10-14)**. Một task/lần; chưa bắt đầu T4.3.

- [x] Compose ps: gateway :8000, CMS :5173, Client :3000 Up; đọc startup, backend_endpoint, master AI-GATE/Phase 4, backend plan, OpenAPI và ports.
- [x] Nối Siamese 128d thật → Milvus COSINE/HNSW (M=16, efConstruction=200); index video mới và backfill video đã xử lý.
- [x] Validate ảnh/ngưỡng, lọc processed+published, thumbnail thật, Redis cache TTL120s/revision và xóa vector/invalidation.
- [x] Go vet/test/build + CMS tsc/Vite + Client tsc/Next FULL lint/build PASS. Python 23 PASS + opt-in real HNSW 1 PASS. Playwright cuối **3 PASS (40,6s)** sau Session/restart; cả T4.1 và T4.2, không HTTP mock.
- [x] HTTP 20 cache misses: p95 **86,30ms**, max **97,54ms**; 20 cache hits: p95 **51,51ms**, max **51,59ms**. HNSW ef100: exact-cosine ANN Recall@10=1,0, p95 **4,89ms**; index Finished/0 pending. Backfill 2 lần và recreate Milvus/inference vẫn **18 live vectors** từ 2 video.
- [x] Báo cáo `docs/T4.2_bao_cao.md`, số liệu JSON, screenshot thật mobile/desktop `test-results/t42-final`; cập nhật master. Inference/gateway/Milvus và CMS/Client đều Up/healthy; không publish/sửa/xóa data người dùng có sẵn.

Changed: real Siamese frame index/search + private MinIO thumbnail + Redis + validate/privacy/delete retry; Compose bật Milvus và pin SDK compatibility.
Verified: số đo/checks ở trên; CPU corpus local nhỏ, model đã warm ở startup. Strong control 400ms được giữ trong báo cáo; Session tối ưu, Go rechecks DB trên cache hit.
Contract touched: no (OpenAPI/ports không đổi).
Next safe task: **T4.3** — VRAM ≤4GB và leak 20 video; chưa bắt đầu. Chưa commit/push.
Limits: chỉ đo 18 live corpus vectors + 8 frame fixture E2E, chưa kiểm tải/corpus lớn/GPU. Top100 candidate rồi lọc public có thể thiếu hit khi private frames lấn át; `shortcut:` + báo cáo ghi rõ. Two-Tower, memory adapters, API gaps T3.1/T3.2 và Mini-GPT limitation giữ nguyên.

## Task trước — T3.2 Client Design Parity

Task vừa thực hiện: **T3.2 — sửa Client theo stitch_ai_video_platform_vietnamese: UI IMPLEMENTED / VERIFIED; DESIGN PARITY FULL = PARTIAL**. Không tick master DONE 100% khi còn contract gaps. T4.2/T4.3 chưa bắt đầu.

- [x] Kiểm compose và đọc startup/client_screen, plan §3/4/5/8, OpenAPI/types và Stitch mobile/desktop từng màn.
- [x] Khung chung/font/ảnh local/SVG đúng path + viewBox, input-wrap padding, responsive.
- [x] Auth → Onboarding → Feed → Video detail → Search → Library/Profile → Discovery; gọi API hiện có, không fake analytics/AI results.
- [x] Go vet/test/build + CMS tsc/Vite + Client lint/tsc/Next FULL build và Docker build PASS, không bỏ lint.
- [x] Playwright cuối trên Client Docker: **42 PASS (1,7 phút)** gồm 38 UI + 2 player logic + 2 flow AI thật. Không SVG fallback, overflow hay pageerror ở 390×844/1440×900.
- [x] Upload >16 MiB → AI thật CPU → processed → duyệt → publish → Feed video.play/currentTime >0,2s → detail seek 1s + play >1,2s và summary đã duyệt. Invalid bytes failed/private. Cleanup chỉ data test.
- [x] Design Parity 10 mục + screenshots: docs/T3.2_client_design_parity.md; source không sửa, trạng thái cập nhật.

Runtime: Docker Desktop được khởi động lại ở phiên tiếp tục; dữ liệu/volumes giữ nguyên. Client image mới đã recreate tại :3000, CMS :5173/gateway :8000 và hạ tầng Up/healthy. Fonts/ảnh HTTP200. Inference CPU, stub_mode=false, 6 models loaded. Visual API thật HTTP503 AI_UNAVAILABLE: chưa có Siamese/Milvus index (T4.2).

Gaps: VideoDetail chưa có URL video gốc (chỉ phát clip published); không GET saved-list/playlist/DELETE likes/history, notification/quick login hoặc analytics count. UI disabled/notice rõ ràng. Personal library mobile thiếu theme config gốc: dùng token cặp desktop. Preferences/history/likes backend còn memory. Mini-GPT T1.6c limitation giữ nguyên.

Changed: toàn bộ Client mobile/desktop theo Stitch, player/media thật, auth/forms, query/state handling và self-host assets.
Verified: 42 PASS (1,7m), builds/checks ở trên; screenshot trong test-results/client-release; SVG/Range/ASR blank và selector Thể thao đã sửa.
Contract touched: no.
Next safe task: backend/contract nguồn phát video gốc và thư viện để đóng parity FULL; sau đó T4.2. Chưa bắt đầu task khác; chưa commit/push.

## Task trước — CMS

# TodoWrite — T3.1 CMS Design Parity

Task vừa thực hiện: **T3.1 — sửa toàn bộ CMS theo stitch_ai_video_cms: UI IMPLEMENTED / VERIFIED; DESIGN PARITY FULL = PARTIAL**, theo yêu cầu mới. Không tick master T3.1 DONE 100% khi còn các phần thiếu API. T4.2/T4.3 chưa bắt đầu.

- [x] Kiểm compose: gateway/CMS/client Up; đọc startup, CMS plan §3/§7 và checklist Design Parity.
- [x] Khung chung/sidebar/topbar, typography/tokens, SVG icons và responsive; Inter/JetBrains Mono lưu trong CMS, không phụ thuộc font icon/CDN runtime.
- [x] Dashboard → Upload/Queue → Video → Highlight → Phụ đề/Tóm tắt → Thư viện → Danh mục → Settings, tuần tự từng màn; CMS build PASS mỗi bước.
- [x] Login/Users đồng bộ icon/form/states; remember local/session; forgot/reset nối API dev có sẵn.
- [x] CMS build, Go vet/test/build, client tsc/Next --no-lint build PASS; 30 case khác nhau Playwright PASS, gồm flow AI thật/MinIO và screenshot 1440×900/390×844; 7 case bị chỉnh cuối PASS lại.
- [x] Báo cáo Design Parity 10 mục + screenshot cùng viewport: docs/T3.1_cms_design_parity.md; cập nhật trạng thái.

Đã xác minh: Go vet/test/build và Client tsc/Next --no-lint PASS. Playwright 29 PASS (50,5s) + forgot/reset 1 PASS (1,7s); sửa lỗi đóng drawer mobile, toast che nút/không tự hết hạn, login 401 bị refresh làm mất lỗi, canvas dùng CSS var trực tiếp khiến sai màu, SVG dùng nhầm viewBox. Contract gap: nguồn phát video gốc/metadata/analytics/quy tắc và một số editor field chưa có API; khóa thao tác/hiện chưa có dữ liệu. Settings backend GET trả defaults và PUT chưa persist: UI báo lỗi khi kiểm tra lại, key chỉ đọc. Không sửa backend/OpenAPI trong task UI này. CMS đã rebuild/recreate; gateway/CMS/client và các services đang Up/healthy. Chưa commit/push.

Changed: toàn bộ giao diện CMS và các tương tác có API, fonts/SVG local, responsive, form/toast/heatmap.
Verified: 30 case khác nhau PASS + build/check ở trên; nguồn clip published phát thật.
Xác minh cuối: video_flow 2 PASS (35,1s), player.play() thành công và currentTime >0,2s, có screenshot cms-published-player.png trong test-results/cms-real-final; CMS HTTP 200, inference CPU/stub_mode=false/6 model loaded. Diff check PASS.
Contract touched: no.
Next safe task: bổ sung backend/contract nguồn phát video gốc và Settings persistence để đóng Design Parity đầy đủ; chưa bắt đầu task khác.

## Task trước — T4.1 (đã hoàn thành, giữ nguyên bằng chứng)

Branch: phase1-ai-core. Task duy nhất: T4.1. Trạng thái: **DONE — REAL UPLOAD/AI FLOW**.

- [x] Đọc startup/master §0/§3/backend §5/§7/OpenAPI/ports và kiểm compose ps; không làm lại task cũ.
- [x] Nginx 2049 MiB request / gateway 2 GiB file; multipart 8 MiB memory + stream MinIO.
- [x] Nối PostgreSQL metadata/user/session, Mongo analysis/subtitles, MinIO, Kafka, Redis và inference checkpoint thật.
- [x] PyAV ingest 1fps/WAV/audio feature 64-d; truyền per-video embeddings; batch/window inference; bỏ silent mock fallback.
- [x] Sửa job SQL cast, Kafka topic/partition startup, Mongo text-index language override, proxy DNS; derive clip score từ timeline thật.
- [x] Go vet/test/build + integration PostgreSQL/Mongo PASS; Python 19 PASS; CMS tsc/Vite PASS; Client tsc/Next --no-lint PASS; E2E tsc PASS.
- [x] Playwright **2 passed (21.7s)**, file >16 MiB qua CMS; Vision/ASR/Highlight/Mini-GPT 200; draft privacy, publish/feed và MinIO bytes 206.
- [x] verify_persistence.ps1 PASS: video/timeline/subtitles/summary và CMS proxy còn sau gateway restart. Giữ video T4.1-REAL-AI-SMOKE: vid_dm3nf6fi23us.
- [x] Cập nhật master plan, e2e README và docs/T4.1_bao_cao.md.

Giới hạn: CPU hiện tại; chưa test nguyên file 2 GiB/video dài/VRAM/leak. Ổ E chỉ còn khoảng 2 GiB. Mini-GPT giữ limitation T1.6c. Siamese/Milvus/vector recommendation chưa nối (503; feed fallback dữ liệu published thật). Preferences/vector/interactions/reset-token memory và player UX chưa hoàn thiện; không claim production toàn bộ hệ thống.

Changed: upload lớn + pipeline AI thật + lưu trữ/events/cache thật.
Verified: kiểm thử/build/persistence như trên; runtime healthy/Up.
Contract touched: no (OpenAPI/ports giữ nguyên).
Next safe task: T4.2; chưa bắt đầu. Chưa commit/push.
