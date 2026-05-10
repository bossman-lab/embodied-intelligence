#!/bin/bash
# 运行GEN72-EG2机器人训练和测试的脚本
# 使用稳定版PPO实现

# 设置ManiSkill根目录
MANISKILL_ROOT="/home/kewei/17robo/ManiSkill"
# cd $MANISKILL_ROOT

export CUDA_VISIBLE_DEVICES=0

# 默认Python路径
PYTHON="/home/kewei/micromamba/envs/dl/bin/python"

# 设置环境变量
export PYTHONPATH=$MANISKILL_ROOT:$PYTHONPATH

# PPO脚本路径
PPO_SCRIPT="$MANISKILL_ROOT/examples/baselines/ppo_my/ppo_my.py"

# 输出目录
OUTPUT_DIR="$MANISKILL_ROOT/examples/baselines/ppo_my/runs"
mkdir -p $OUTPUT_DIR

# 模型保存目录 - 通过环境变量传递给Python脚本
export MODEL_SAVE_DIR=$OUTPUT_DIR

echo "====== GEN72-EG2 机器人训练/评估脚本 ======"
echo "使用稳定版PPO实现"
echo "模型将保存在: $OUTPUT_DIR"

# 训练函数
train() {
    local task=$1
    local mode=$2
    
    case "$mode" in
        "default")
            echo "[1/3] 开始训练 ${task} (默认配置)..."
            $PYTHON $PPO_SCRIPT \
                --robot_uids="gen72_eg2_robot" \
                --env_id="${task}" \
                --control_mode="pd_joint_delta_pos" \
                --num_envs=256 \
                --total_timesteps=10000000 \
                --learning_rate=1e-4 \
                --max_grad_norm=0.25 \
                --eval_freq=10
            ;;
        "stable")
            echo "[1/3] 开始训练 ${task} (稳定配置)..."
            $PYTHON $PPO_SCRIPT \
                --robot_uids="gen72_eg2_robot" \
                --env_id="${task}" \
                --control_mode="pd_joint_delta_pos" \
                --num_envs=128 \
                --total_timesteps=10000000 \
                --learning_rate=5e-5 \
                --max_grad_norm=0.25 \
                --update_epochs=4 \
                --num_minibatches=4 \
                --eval_freq=10
            ;;
        "ultra-stable")
            echo "[1/3] 开始训练 ${task} (超稳定配置)..."
            $PYTHON $PPO_SCRIPT \
                --robot_uids="gen72_eg2_robot" \
                --env_id="${task}" \
                --control_mode="pd_joint_delta_pos" \
                --num_envs=32 \
                --num_steps=8 \
                --total_timesteps=10000000 \
                --learning_rate=1e-5 \
                --max_grad_norm=0.15 \
                --update_epochs=1 \
                --num_minibatches=1 \
                --eval_freq=20
            ;;
        "fast")
            echo "[1/3] 开始训练 ${task} (快速配置)..."
            $PYTHON $PPO_SCRIPT \
                --robot_uids="gen72_eg2_robot" \
                --env_id="${task}" \
                --control_mode="pd_joint_delta_pos" \
                --num_envs=512 \
                --total_timesteps=5000000 \
                --learning_rate=1e-4 \
                --max_grad_norm=0.25 \
                --eval_freq=5
            ;;
        *)
            echo "未知的训练模式: $mode"
            exit 1
            ;;
    esac
}

# 评估函数
evaluate() {
    local task=$1
    local checkpoint=$2
    
    echo "[2/3] 评估模型 ${checkpoint} 在 ${task}..."
    $PYTHON $PPO_SCRIPT \
        --robot_uids="gen72_eg2_robot" \
        --env_id="${task}" \
        --control_mode="pd_joint_delta_pos" \
        --evaluate \
        --checkpoint="${checkpoint}" \
        --num_eval_envs=1 \
        --num-eval-steps=1000
}

# 根据传入的参数执行相应的操作
case "$1" in
    "train")
        if [ -z "$2" ]; then
            echo "请指定任务: ./run_gen72_ppo.sh train [PushCube-v1|PickCube-v1] [default|stable|ultra-stable|fast]"
            exit 1
        fi
        
        mode="stable"
        if [ ! -z "$3" ]; then
            mode="$3"
        fi
        
        train "$2" "$mode"
        ;;
    "evaluate")
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "请指定任务和模型: ./run_gen72_ppo.sh evaluate [PushCube-v1|PickCube-v1] [模型路径]"
            exit 1
        fi
        
        evaluate "$2" "$3"
        ;;
    "push-cube")
        # PushCube快速训练预设
        train "PushCube-v1" "fast"
        ;;
    "pick-cube")
        # PickCube稳定训练预设
        train "PickCube-v1" "stable"
        ;;
    *)
        echo "使用方法:"
        echo "  ./run_gen72_ppo.sh train [任务名称] [训练模式]  - 训练GEN72-EG2机器人"
        echo "    任务名称: PushCube-v1, PickCube-v1"
        echo "    训练模式: default, stable, ultra-stable, fast"
        echo "  ./run_gen72_ppo.sh evaluate [任务名称] [模型路径]  - 评估训练好的模型"
        echo ""
        echo "  预设命令:"
        echo "  ./run_gen72_ppo.sh push-cube  - 快速训练PushCube任务"
        echo "  ./run_gen72_ppo.sh pick-cube  - 稳定训练PickCube任务"
        echo ""
        echo "示例:"
        echo "  ./run_gen72_ppo.sh train PushCube-v1 stable"
        echo "  ./run_gen72_ppo.sh evaluate PushCube-v1 $OUTPUT_DIR/PushCube-v1__ppo_my__1__1234567890/final_ckpt.pt"
        ;;
esac

echo "[3/3] 完成!" 