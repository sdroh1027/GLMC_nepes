
20230530 지희

* 사용한 명령어(root는 3090*4서버 기준):
python main.py --dataset nepes -a resnet50 --num_classes 10 --beta 0.5 --lr 0.01 --epochs 1000 -b 64 --momentum 0.9 --weight_decay 5e-3 --resample_weighting 0.0 --label_weighting 1.2 --contrast_weight 4 --root /home/user/dataset/datasets/Bulryang3/camtek_v3_train_valid_2
* 키메라 완료 단계라 코드 정리중입니다.. 정확도 엑셀로 뽑는 등 기능 추가 예정
* 위 명령어로 1000epoch 결과(11h 소요):
many avg, med avg, few avg 62.945430594058635 66.96832579185521 59.999999999999986
Best Prec@1: 70.309
* 에포크 늘리면 더 높아질 수도
* 데이터셋은 nepes_dataset_description_v3.txt에 적혀있던 대로 17개 클래스로 줄였습니다
* 앞으로 할 것: ResNet-50에서 한번 더 돌려보기, 하이퍼파라미터 최적화, 에포크 증가,..
* + 다시보니 resnext50_32x4d.. resnet50으로 수정

=> creating model 'resnet50'
  + Number of params: 24.16M
=> creating model 'resnext50_32x4d'
  + Number of params: 23.64M

======================================================================================

