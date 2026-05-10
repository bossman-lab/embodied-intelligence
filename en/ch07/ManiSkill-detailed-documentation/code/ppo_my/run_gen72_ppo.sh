#!/bin/bash
# Script to train and test the GEN72-EG2 robot using the stable PPO implementation

# ManiSkill root directory
MANISKILL_ROOT="/home/kewei/17robo/ManiSkill"
# cd $MANISKILL_ROOT

export CUDA_VISIBLE_DEVICES=0

# Default Python interpreter
PYTHON="/home/kewei/micromamba/envs/dl/bin/python"

# Environment variables
export PYTHONPATH=$MANISKILL_ROOT:$PYTHONPATH

# PPO script path
PPO_SCRIPT="$MANISKILL_ROOT/examples/baselines/ppo_my/ppo_my.py"

# Output directory
OUTPUT_DIR="$MANISKILL_ROOT/examples/baselines/ppo_my/runs"
mkdir -p $OUTPUT_DIR

# Model-save directory – passed to the Python script via env var
export MODEL_SAVE_DIR=$OUTPUT_DIR

echo "====== GEN72-EG2 Robot Training/Test Script ======"
echo "Using stable PPO implementation"
echo "Models will be saved to: $OUTPUT_DIR"

# ---------- Training function ----------
train() {
    local task=$1
    local mode=$2

    case "$mode" in
        "default")
            echo "[1/3] Starting ${task} training (default config)..."
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
            echo "[1/3] Starting ${task} training (stable config)..."
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
            echo "[1/3] Starting ${task} training (ultra-stable config)..."
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
            echo "[1/3] Starting ${task} training (fast config)..."
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
            echo "Unknown training mode: $mode"
            exit 1
            ;;
    esac
}

# ---------- Evaluation function ----------
evaluate() {
    local task=$1
    local checkpoint=$2

    echo "[2/3] Evaluating ${checkpoint} on ${task}..."
    $PYTHON $PPO_SCRIPT \
        --robot_uids="gen72_eg2_robot" \
        --env_id="${task}" \
        --control_mode="pd_joint_delta_pos" \
        --evaluate \
        --checkpoint="${checkpoint}" \
        --num_eval_envs=1 \
        --num-eval-steps=1000
}

# ---------- Main argument handling ----------
case "$1" in
    "train")
        if [ -z "$2" ]; then
            echo "Please specify a task: ./run_gen72_ppo.sh train [PushCube-v1|PickCube-v1] [default|stable|ultra-stable|fast]"
            exit 1
        fi

        mode="stable"
        if [ -n "$3" ]; then
            mode="$3"
        fi

        train "$2" "$mode"
        ;;
    "evaluate")
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "Please specify a task and a model: ./run_gen72_ppo.sh evaluate [PushCube-v1|PickCube-v1] [model_path]"
            exit 1
        fi

        evaluate "$2" "$3"
        ;;
    "push-cube")
        # Quick training preset for PushCube
        train "PushCube-v1" "fast"
        ;;
    "pick-cube")
        # Stable training preset for PickCube
        train "PickCube-v1" "stable"
        ;;
    *)
        echo "Usage:"
        echo "  ./run_gen72_ppo.sh train [task_name] [training_mode]  – train GEN72-EG2 robot"
        echo "    task_name: PushCube-v1, PickCube-v1"
        echo "    training_mode: default, stable, ultra-stable, fast"
        echo "  ./run_gen72_ppo.sh evaluate [task_name] [model_path]  – evaluate a trained model"
        echo ""
        echo "  Preset shortcuts:"
        echo "  ./run_gen72_ppo.sh push-cube  – fast training for PushCube"
        echo "  ./run_gen72_ppo.sh pick-cube  – stable training for PickCube"
        echo ""
        echo "Examples:"
        echo "  ./run_gen72_ppo.sh train PushCube-v1 stable"
        echo "  ./run_gen72_ppo.sh evaluate PushCube-v1 $OUTPUT_DIR/PushCube-v1__ppo_my__1__1234567890/final_ckpt.pt"
        ;;
esac

echo "[3/3] Done!"